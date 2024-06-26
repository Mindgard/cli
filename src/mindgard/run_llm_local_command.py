import json
import logging
from typing import Dict, Any, Callable, Literal, Optional, List
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

# Networking
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

# Exceptions
from .exceptions import (
    MGException,
    ServiceUnavailable,
    InternalServerError,
    RateLimitOrInsufficientCredits,
    FailedDependency,
    UnprocessableEntity,
    Timeout,
    NotFound,
    BadRequest,
    Forbidden,
    Unauthorized,
    Uncontactable,
    HTTPBaseError,
    EmptyResponse,
    NotImplemented
)

# Types
from typing import Type

import time

from .wrappers import ModelWrapper, ContextManager

from .utils import CliResponse

from .auth import require_auth
from .api_service import ApiService

TEST_POLL_INTERVAL = 5
ErrorCode = Literal["CouldNotContact", "ContentPolicy", "CLIError", "NotImplemented", "NoResponse", "RateLimited", "NetworkIssue", "MaxContextLength"]


exceptions_to_cli_status_codes: Dict[Type[Exception], ErrorCode] = {
    Uncontactable: "CouldNotContact",
    BadRequest: "NoResponse", # not sure about this, we don't handle 400 atm
    Unauthorized: "NoResponse",
    Forbidden: "NoResponse",
    NotFound: "NoResponse",
    Timeout: "NoResponse",
    UnprocessableEntity: "NoResponse", # this is currently being handled as a rate limit issue for some reason
    FailedDependency: "NoResponse",
    RateLimitOrInsufficientCredits: "RateLimited",
    InternalServerError: "NoResponse",
    ServiceUnavailable: "NoResponse",
    NotImplemented: "NotImplemented",
    EmptyResponse: "NoResponse"
}


def handle_exception_callback(exception: Exception, handle_visual_exception_callback: Optional[Callable[[str], None]]) -> ErrorCode:
    # TODO - come take a look at this
    error_code: ErrorCode = exceptions_to_cli_status_codes.get(type(exception), "CLIError") # type: ignore
    callback_text = str(exception)

    if handle_visual_exception_callback:
        handle_visual_exception_callback(callback_text)

    logging.debug(exception)
    return error_code


class RunLLMLocalCommand:
    def __init__(
        self,
        api_service: ApiService,
        model_wrapper: ModelWrapper,
        parallelism: int,   
        poll_interval: float = TEST_POLL_INTERVAL,
    ) -> None:
        self._api = api_service
        self._poll_interval = poll_interval  # poll interval is expose to speed up tests
        self._model_wrapper = model_wrapper
        self._parallelism = parallelism
        self._context_manager = ContextManager()

    @staticmethod
    def validate_args(args:Dict[str, Any]) -> None:
        # args must include non-zero values for 
        # target: str, json_format: bool, risk_threshold: int, system_prompt: str
        missing_args: List[str]= []
        if args.get("target") == None or args.get("target") == "":
            missing_args.append("target")
        if args.get("system_prompt", None) is None:
            missing_args.append("system_prompt")
        if args['parallelism'] < 1:
            raise ValueError(f"--parallelism must be a positive integer")
        if len(missing_args) > 0:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")


    def submit_test_progress(
        self, progress: Progress, access_token: str, target: str, system_prompt: str, error_callback: Callable[[Exception], ErrorCode]
    ) -> Dict[str, Any]:
        with progress:
            with ThreadPoolExecutor() as pool:
                task_id = progress.add_task("Submitting test...", start=True)

                future = pool.submit(
                    self.submit_test_fetching_initial, access_token, target, system_prompt, error_callback
                )

                while not future.done():
                    progress.update(task_id, refresh=True)
                    sleep(0.1)
                progress.update(task_id, completed=100)
                return future.result()

    def submit_test_fetching_initial(
        self, access_token: str, target: str, system_prompt: str, error_callback: Callable[[Exception], ErrorCode]
    ) -> Dict[str, Any]:
        ws_token_and_group_id = (
            self._api.get_orchestrator_websocket_connection_string(
                access_token=access_token, payload={"target": target, "system_prompt": system_prompt, "parallelism": self._parallelism}
            )
        )

        url = ws_token_and_group_id.get("url", None)
        group_id = ws_token_and_group_id.get("groupId", None)

        if url is None:
            raise Exception(
                "URL from API server missing for LLM forwarding!"
            )
        if group_id is None:
            raise Exception(
                "groupId from API server missing for LLM forwarding!"
            )

        # Should fire the connect event on the orchestrator
        credentials = WebPubSubClientCredential(client_access_url_provider=url)
        ws_client = WebPubSubClient(credential=credentials)

        self.submitted_test = False
        self.submitted_test_id = ""

        # this guy is difficult to manage exceptions for as websocket messages are event-based.
        # the recv message handler also has no idea which messages are for which attack, so
        # we can't mark an attack as failed until we are complete
        def recv_message_handler(msg: OnGroupDataMessageArgs) -> None:
            if msg.data["messageType"] == "Request":
                logging.debug(f"received request {msg.data=}")
                context_id = msg.data["payload"].get("context_id", None)
                context = self._context_manager.get_context_or_none(context_id)
                content = msg.data["payload"]["prompt"]

                response: str = ""
                error_code: Optional[ErrorCode] = None

                try:
                    # would pose being explicit with __call__ so we can ctrl+f easier, not a very clear shorthand
                    response = self._model_wrapper.__call__(
                        content=content,
                        with_context=context,
                    )
                except MGException as mge:
                    error_code = error_callback(mge)
                    if error_code == "CLIError":
                        raise mge
                except Exception as e:
                    raise e
                finally:
                    # we always try to send a response
                    replyData = {
                        "correlationId": msg.data["correlationId"],
                        "messageType": "Response",
                        "status": "ok", # Deprecated but kept for compatibility
                        "payload": {
                            "response": response,
                            "error": error_code,
                        }
                    }
                    logging.debug(f"sending response {replyData=}")

                    ws_client.send_to_group("orchestrator", replyData, data_type="json") # type: ignore
            elif msg.data["messageType"] == "StartedTest": # should be something like "Submitted", upstream change required.
                self.submitted_test_id = msg.data["payload"]["testId"]
                self.submitted_test = True
            else:
                pass

        ws_client.open()

        ws_client.subscribe("group-message", recv_message_handler) # type: ignore

        payload = {
            "correlationId": "",
            "messageType": "StartTest",
            "payload": {"groupId": ws_token_and_group_id["groupId"]},
        }

        ws_client.send_to_group(group_name="orchestrator", content=payload, data_type="json") # type: ignore

        # wait 
        max_attempts = 30
        attempts_remaining = max_attempts
        while not self.submitted_test:
            time.sleep(1)
            attempts_remaining -= 1
            if attempts_remaining == 0:
                break

        # we're here if submitting was a success...

        if attempts_remaining !=0:
            return self._api.get_test(access_token, self.submitted_test_id)
        else:
            raise Exception(f"did not receive notification of test submitted within timeout ({max_attempts}s); failed to start test")

    def run_inner(
        self, access_token: str, target: str, json_format: bool, 
        risk_threshold: int, system_prompt: str, console: Console
    ) -> CliResponse:

        if json_format:
            return self.run_json(
                access_token=access_token, target=target, risk_threshold=risk_threshold, system_prompt=system_prompt
            )

        progress_table = Table.grid(expand=True)

        submit_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text="[green3] Submitted!"),
            auto_refresh=True,
        )

        exceptions_progress = Progress(
            "{task.description}"
        )

        exceptions_task_table: Dict[str, TaskID] = {}
        exceptions_count_table: Dict[str, int] = {}

        def _handle_visual_exception_callback(text: str) -> None:
            if not exceptions_task_table.get(text, None):
                exceptions_count_table[text] = 0
                exceptions_task_table[text] = exceptions_progress.add_task("")

            exceptions_count_table[text] += 1
            exceptions_progress.update(
                exceptions_task_table[text],
                description=f"[dark_orange3][!!!] {text} (x{exceptions_count_table[text]})"
            )


        test_res: Dict[str, Any]
        with submit_progress:
            test_res = self.submit_test_progress(
                submit_progress, access_token=access_token, target=target, system_prompt=system_prompt,
                error_callback=lambda x: handle_exception_callback(x, _handle_visual_exception_callback)
            )

        attacks = test_res["attacks"]
        test_id = test_res["id"]
        attack_count = len(attacks)

        overall_progress = Progress()
        overall_task = overall_progress.add_task("Assessment Progress", total=attack_count)

        attacks_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text="done"),
            TextColumn("{task.fields[status]}")
        )
        attacks_task_map: Dict[str, TaskID] = {}
        for attack in attacks:
            attacks_task_map[attack["id"]] = attacks_progress.add_task(
                f"Attack {attack['attack']}", total=1, status="[chartreuse1]queued"
            )

        progress_table.add_row(overall_progress)
        progress_table.add_row(attacks_progress)
        progress_table.add_row("")
        progress_table.add_row(exceptions_progress)


        with Live(progress_table, refresh_per_second=10):
            while not overall_progress.finished:
                sleep(self._poll_interval)
                test_res = self._api.get_test(access_token, test_id=test_id)

                for attack_res in test_res["attacks"]:
                    task_id = attacks_task_map[attack_res["id"]]
                    if attack_res["state"] == 2:
                        attacks_progress.update(task_id, completed=1, status="[chartreuse3]success")
                    elif attack_res["state"] == -1:
                        attacks_progress.update(task_id, completed=1, status="[red3]failed")
                    elif attack_res["state"] == 1:
                        attacks_progress.update(task_id, status="[orange3]running")


                completed = sum(task.completed for task in attacks_progress.tasks)
                overall_progress.update(overall_task, completed=completed)

        table = Table(
            title=f"Results - https://sandbox.mindgard.ai/r/test/{test_id}", width=80
        )
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Risk", justify="right", style="green")

        for attack in test_res["attacks"]:
            if attack["state"] != 2:
                attack_name = attack["attack"]
                name = f"Error running '{attack_name}'"
                risk_str = "n/a"
                emoji = "❗️"
            else:
                name = attack["attack"]
                risk = attack["risk"]
                risk_str = str(risk)
                emoji = "❌‍" if risk > risk_threshold else "✅️"

            table.add_row(emoji, name, risk_str)

        console.print(table)

        return CliResponse(
            self.calculate_exit_code(test_res=test_res, risk_threshold=risk_threshold)
        )

    @require_auth
    def run(
        self, access_token: str, target: str, json_format: bool, risk_threshold: int, system_prompt: str, console: Console
    ) -> CliResponse:
        """
        Run the command.

        Returns int of exit code
        """
        return self.run_inner(
            access_token=access_token,
            json_format=json_format,
            target=target,
            risk_threshold=risk_threshold,
            system_prompt=system_prompt,
            console=console
        )

    def run_json(
        self, access_token: str, target: str, risk_threshold: int, system_prompt:str
    ) -> CliResponse:
        test_res = self.submit_test_fetching_initial(
            access_token=access_token, target=target, system_prompt=system_prompt, error_callback=lambda x: handle_exception_callback(x, None)
        )
        test_id = test_res["id"]
        while test_res["hasFinished"] is False:
            sleep(self._poll_interval)
            test_res = self._api.get_test(access_token, test_id=test_id)

        print(json.dumps(test_res))
        return CliResponse(
            self.calculate_exit_code(test_res=test_res, risk_threshold=risk_threshold)
        )

    def calculate_exit_code(self, test_res: Dict[str, Any], risk_threshold: int) -> int:
        if test_res["risk"] > risk_threshold:
            return 1
        else:
            return 0
