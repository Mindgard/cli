import json
from typing import Dict, Any
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TaskID

# Networking
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

import time

from .wrappers import ModelWrapper

from .utils import CliResponse

from .auth import require_auth
from .api_service import ApiService

TEST_POLL_INTERVAL = 5


# command for running tests against the pinch backend;
# MINDGARDIANS ONLY!
class RunLLMLocalCommand:
    def __init__(
        self,
        api_service: ApiService,
        model_wrapper: ModelWrapper,
        poll_interval: float = TEST_POLL_INTERVAL,
    ) -> None:
        self._api = api_service
        self._poll_interval = poll_interval  # poll interval is expose to speed up tests
        self._model_wrapper = model_wrapper

    def submit_test_progress(
        self, progress: Progress, access_token: str, target: str
    ) -> Dict[str, Any]:
        with progress:
            with ThreadPoolExecutor() as pool:
                task_id = progress.add_task("submitting test", start=True)

                future = pool.submit(
                    self.submit_test_fetching_initial, access_token, target
                )

                while not future.done():
                    progress.update(task_id, refresh=True)
                    sleep(0.1)
                progress.update(task_id, completed=100)
                return future.result()

    def submit_test_fetching_initial(
        self, access_token: str, target: str
    ) -> Dict[str, Any]:
        ws_token_and_group_id = (
            self._api.get_orchestrator_websocket_connection_string(
                access_token=access_token, payload={"target": target}
            )
        )
            
        # except req_exception.HTTPError as e:
        #     status_code = e.response.status_code
        #     if status_code == 404:
        #         # don't think this is a possibility anymore
        #         # DEPRECATED
        #         print(f"Requested model ({target}) name has no associated attacks!")
        #         return CliResponse(code=1)
        #     elif status_code == 400:
        #         print(f"Malformed request!")
        #         return CliResponse(code=1)
        #     elif status_code == 403:
        #         print(f"You are forbidden from accessing this feature!")
        #         return CliResponse(code=1)
            
        # except Exception as e:
        #     # TODO: figure out if we want to pass high fidelity logs to user
        #     print("Failed to get credentials from API server for LLM forwarding!")
        #     return CliResponse(code=1)

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

        def recv_message_handler(msg: OnGroupDataMessageArgs):
            if msg.data["messageType"] == "Request":
                replyData = {
                    "correlationId": msg.data["correlationId"],
                    "messageType": "Response",
                    "payload": {
                        "response": self._model_wrapper(
                            prompt=msg.data["payload"]["prompt"]
                        )
                    },
                }
                ws_client.send_to_group("orchestrator", replyData, data_type="json")
            elif msg.data["messageType"] == "StartedTest": # should be something like "Submitted", upstream change required.
                self.submitted_test_id = msg.data["payload"]["testId"]
                self.submitted_test = True
            else:
                pass

        ws_client.open()

        ws_client.subscribe("group-message", recv_message_handler)

        payload = {
            "correlationId": "",
            "messageType": "StartTest",
            "payload": {"groupId": ws_token_and_group_id["groupId"]},
        }

        ws_client.send_to_group(
            group_name="orchestrator", content=payload, data_type="json"
        )

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
        self, access_token: str, target: str, json_format: bool, risk_threshold: int
    ) -> CliResponse:
        if json_format:
            return self.run_json(
                access_token=access_token, target=target, risk_threshold=risk_threshold
            )

        submit_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text=r"\[done]"),
            auto_refresh=True,
        )

        test_res: Dict[str, Any]
        with submit_progress:
            test_res = self.submit_test_progress(
                submit_progress, access_token=access_token, target=target
            )

        attacks = test_res["attacks"]
        test_id = test_res["id"]
        attack_count = len(attacks)

        overall_progress = Progress()
        overall_task = overall_progress.add_task("overall", total=attack_count)

        attacks_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text=r"\[done]"),
        )
        attacks_task_map: Dict[str, TaskID] = {}
        for attack in attacks:
            attacks_task_map[attack["id"]] = attacks_progress.add_task(
                f"attack {attack['attack']}", total=1
            )

        progress_table = Table.grid(expand=True)
        progress_table.add_row(overall_progress)
        progress_table.add_row(attacks_progress)

        with Live(progress_table, refresh_per_second=10):
            while not overall_progress.finished:
                sleep(self._poll_interval)
                test_res = self._api.get_test(access_token, test_id=test_id)

                for attack_res in test_res["attacks"]:
                    task_id = attacks_task_map[attack_res["id"]]
                    if attack_res["state"] == 2:
                        attacks_progress.update(task_id, completed=1)
                    elif attack_res["state"] == -1:
                        attacks_progress.update(task_id, completed=1)

                completed = sum(task.completed for task in attacks_progress.tasks)
                overall_progress.update(overall_task, completed=completed)

        table = Table(
            title=f"Results - https://sandbox.mindgard.ai/r/test/{test_id}", width=80
        )
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Risk", justify="right", style="green")

        for attack in test_res["attacks"]:
            risk = attack["risk"]
            emoji = "❌‍" if risk > risk_threshold else "✅️"
            table.add_row(emoji, attack["attack"], str(risk))

        console = Console()
        console.print(table)

        return CliResponse(
            self.calculate_exit_code(test_res=test_res, risk_threshold=risk_threshold)
        )

    @require_auth
    def run(
        self, access_token: str, target: str, json_format: bool, risk_threshold: int
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
        )

    def run_json(
        self, access_token: str, target: str, risk_threshold: int
    ) -> CliResponse:
        test_res = self.submit_test_fetching_initial(
            access_token=access_token, target=target
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
