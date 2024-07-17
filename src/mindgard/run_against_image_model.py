import json
import logging
from typing import Dict, Any, Callable, Literal, Optional, List
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

from .constants import DASHBOARD_URL

# Networking
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

# API
from .api_service import ApiService

# Types
from typing import Type
from pydantic import BaseModel

# Encoding/decoding
import io
import base64

import time

from .utils import CliResponse, print_to_stderr

from .auth import require_auth

from .image_wrappers import ImageModelWrapper

TEST_POLL_INTERVAL = 5

api_service = ApiService()


class WebPubSubInitialConnection(BaseModel):
    url: str
    groupId: str

class RunImageCommand:
    def __init__(
        self,
        model_wrapper: ImageModelWrapper,
        parallelism: int,   
        poll_interval: float = TEST_POLL_INTERVAL,
    ) -> None:
        self._poll_interval = poll_interval  # poll interval is expose to speed up tests
        self._model_wrapper = model_wrapper
        self._parallelism = parallelism


    @staticmethod
    def validate_args(args:Dict[str, Any]) -> None:
        # args must include non-zero values for 
        # target: str
        missing_args: List[str]= []
        if args.get("target") == None or args.get("target") == "":
            missing_args.append("target")
        if args['parallelism'] < 1:
            raise ValueError(f"--parallelism must be a positive integer")
        if len(missing_args) > 0:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")


    def create_test_request(self, api_key: str, url: str) -> Dict[str, Any]:
        websocket_details_json = api_service.get_orchestrator_websocket_connection_string(access_token=api_key,
                                                                 payload={
                                                                     "url": url,
                                                                     "target": "test_model_0",
                                                                     "modality": "image"
                                                                 })
        
        websocket_details = WebPubSubInitialConnection(**websocket_details_json)
        
        credentials = WebPubSubClientCredential(client_access_url_provider=websocket_details.url)
        ws_client = WebPubSubClient(credential=credentials)

        self.submitted_test = False
        self.submitted_test_id = ""

        def recv_message_handler(msg: OnGroupDataMessageArgs) -> None:
            if msg.data["messageType"] == "Request":
                logging.debug(f"received request {msg.data=}")
                image_bytes = base64.b64decode(msg.data["payload"]["image"])

                try:
                    response = self._model_wrapper.infer(
                        image = image_bytes
                    )
                except Exception as e:
                    raise e
                finally:
                    # we always try to send a response
                    replyData = {
                        "correlationId": msg.data["correlationId"],
                        "messageType": "Response",
                        "status": "ok", # Deprecated but kept for compatibility
                        "payload": {
                            "response": [t.model_dump() for t in response]
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
            "payload": {"groupId": websocket_details.groupId},
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
            return api_service.get_test(api_key, self.submitted_test_id)
        else:
            raise Exception(f"did not receive notification of test submitted within timeout ({max_attempts}s); failed to start test")


    def submit_test_progress(self, progress: Progress, access_token: str) -> Dict[str, Any]:
        with progress:
            with ThreadPoolExecutor() as pool:
                task_id = progress.add_task("Submitting test...", start=True)

                future = pool.submit(
                    self.create_test_request, api_key = access_token, url = self._model_wrapper.url
                )

                while not future.done():
                    progress.update(task_id, refresh=True)
                    sleep(0.1)
                progress.update(task_id, completed=100)
                return future.result()


    def run_inner(self, access_token: str, json_format: bool, console: Console, risk_threshold: int) -> CliResponse:
        if json_format:
            return self.run_json(access_token=access_token, risk_threshold=risk_threshold)

        progress_table = Table.grid(expand=True)

        submit_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text="[green3] Submitted!"),
            auto_refresh=True,
        )

        test_res: Dict[str, Any]
        with submit_progress:
            test_res = self.submit_test_progress(
                submit_progress,
                access_token=access_token
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

        with Live(progress_table, refresh_per_second=10):
            while not overall_progress.finished:
                sleep(self._poll_interval)
                test_res = api_service.get_test(access_token, test_id=test_id)

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
            title=f"Results - {DASHBOARD_URL}/r/test/{test_id}", width=80
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


    def calculate_exit_code(self, test_res: Dict[str, Any], risk_threshold: int) -> int:
        if test_res["risk"] > risk_threshold:
            return 1
        else:
            return 0


    @require_auth
    def run(self, access_token: str, console: Console) -> CliResponse:
        """
        Run the command.

        Returns int of exit code
        """
        return self.run_inner(access_token=access_token, risk_threshold=50, console=console, json_format=False)
    
    def run_json(self, access_token: str, risk_threshold: int) -> CliResponse:
        
        submit_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text="[green3] Submitted!"),
            auto_refresh=True,
        )

        test_res = self.submit_test_progress(
                submit_progress,
                access_token=access_token
            )
        test_id = test_res["id"]
        while test_res["hasFinished"] is False:
            sleep(self._poll_interval)
            test_res = api_service.get_test(access_token, test_id=test_id)

        print(json.dumps(test_res))
        return CliResponse(
            self.calculate_exit_code(test_res=test_res, risk_threshold=risk_threshold)
        )