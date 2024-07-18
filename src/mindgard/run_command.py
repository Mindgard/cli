# Typing
from .utils import CliResponse
from typing import Any, Dict, Callable, Optional, Literal, Type, cast, List, Union
from dataclasses import dataclass
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs
from .wrappers import ModelWrapper
from pydantic import BaseModel

# UI
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn
from rich.console import Console
from rich.live import Live

# Exceptions
from .exceptions import *

# Auth
from .auth import require_auth

# API
from .api_service import ApiService
import json

# Logging
import logging

# Misc
from time import sleep

# Constants
from .constants import API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS, DASHBOARD_URL


api_service = ApiService()


# Type aliases
# access token, target,
# parallelism, model_wrapper,
# visual_exception_callback, modality_specific_args
type_submit_test_function = Callable[
    [str, str, int, ModelWrapper, Callable[[str], None], Optional[BaseModel]],
    List[str],
]


@dataclass
class WebsocketDetails:
    group_id: str
    url: str
    credentials: WebPubSubClientCredential
    ws_client: WebPubSubClient


def websocket_initial_connection(
    ws_client: WebPubSubClient,
    message_handler: Callable[[OnGroupDataMessageArgs], None],
    group_id: str,
) -> None:
    ws_client.open()

    ws_client.subscribe("group-message", message_handler)  # type: ignore

    payload = {
        "correlationId": "",
        "messageType": "StartTest",
        "payload": {"groupId": group_id},
    }

    ws_client.send_to_group(group_name="orchestrator", content=payload, data_type="json")  # type: ignore


def message_handler_function_factory(
    request_callback: Callable[[OnGroupDataMessageArgs], Dict[str, str]],
    submitted_callback: Callable[[str], None],
    ws_client: WebPubSubClient,
) -> Callable[[OnGroupDataMessageArgs], None]:

    def recv_message_handler(msg: OnGroupDataMessageArgs) -> None:
        if msg.data["messageType"] == "Request":
            logging.debug(f"received request {msg.data=}")
            # TODO: Check if these exceptions are raised properly
            try:
                reply_data = request_callback(msg)
            except Exception as e:
                raise e
            logging.debug(f"sending response {reply_data=}")

            ws_client.send_to_group("orchestrator", reply_data, data_type="json")  # type: ignore
        elif (
            msg.data["messageType"] == "StartedTest"
        ):  # should be something like "Submitted", upstream change required.
            submitted_callback(msg.data["payload"]["testId"])
        else:
            pass

    return recv_message_handler


def create_websocket_and_get_details(
    access_token: str,
    target: str,
    parallelism: int,
    modality: str,
    payload: Dict[str, str],
) -> WebsocketDetails:
    ws_token_and_group_id = api_service.get_orchestrator_websocket_connection_string(
        access_token=access_token,
        payload={
            "target": target,
            "parallelism": parallelism,
            "modality": modality,
            **payload,
        },
    )

    url = ws_token_and_group_id.get("url", None)
    group_id = ws_token_and_group_id.get("groupId", None)

    if url is None:
        raise Exception("URL from API server missing for LLM forwarding!")
    if group_id is None:
        raise Exception("groupId from API server missing for LLM forwarding!")

    # Should fire the connect event on the orchestrator
    credentials = WebPubSubClientCredential(client_access_url_provider=url)
    ws_client = WebPubSubClient(credential=credentials)

    return WebsocketDetails(
        group_id=group_id, ws_client=ws_client, credentials=credentials, url=url
    )


def poll_for_successful_submission(submitted_id: List[str]) -> str:
    max_attempts = 30
    attempts_remaining = max_attempts
    while submitted_id[0] == "":
        sleep(1)
        attempts_remaining -= 1
        if attempts_remaining == 0:
            break

    # we're here if submitting was a success...
    if attempts_remaining != 0:
        return submitted_id[0]
    else:
        raise Exception(
            f"did not receive notification of test submitted within timeout ({max_attempts}s); failed to start test"
        )


def run_test_with_ui(
    access_token: str,
    target: str,
    parallelism: int,
    risk_threshold: int,
    model_wrapper: ModelWrapper,
    submit_test_function: type_submit_test_function,
    modality_specific_args: Optional[BaseModel | None] = None,
) -> CliResponse:
    console = Console()
    progress_table = Table.grid(expand=True)
    submit_progress = Progress(
        "{task.description}",
        SpinnerColumn(finished_text="[green3] Submitted!"),
        auto_refresh=True,
    )
    exceptions_progress = Progress("{task.description}")
    exceptions_task_table: Dict[str, TaskID] = {}
    exceptions_count_table: Dict[str, int] = {}

    def _handle_visual_exception_callback(text: str) -> None:
        if not exceptions_task_table.get(text, None):
            exceptions_count_table[text] = 0
            exceptions_task_table[text] = exceptions_progress.add_task("")

        exceptions_count_table[text] += 1
        exceptions_progress.update(
            exceptions_task_table[text],
            description=f"[dark_orange3][!!!] {text} (x{exceptions_count_table[text]})",
        )

    with submit_progress:
        submitted_id = submit_test_function(
            access_token,
            target,
            parallelism,
            model_wrapper,
            _handle_visual_exception_callback,
            modality_specific_args,
        )

    test_id = poll_for_successful_submission(submitted_id)
    test_res = api_service.get_test(access_token=access_token, test_id=test_id)

    attacks = test_res["attacks"]
    test_id = test_res["id"]
    attack_count = len(attacks)

    overall_progress = Progress()
    overall_task = overall_progress.add_task("Assessment Progress", total=attack_count)

    attacks_progress = Progress(
        "{task.description}",
        SpinnerColumn(finished_text="done"),
        TextColumn("{task.fields[status]}"),
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
            sleep(API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS)
            test_res = api_service.get_test(access_token, test_id=test_id)

            for attack_res in test_res["attacks"]:
                task_id = attacks_task_map[attack_res["id"]]
                if attack_res["state"] == 2:
                    attacks_progress.update(
                        task_id, completed=1, status="[chartreuse3]success"
                    )
                elif attack_res["state"] == -1:
                    attacks_progress.update(task_id, completed=1, status="[red3]failed")
                elif attack_res["state"] == 1:
                    attacks_progress.update(task_id, status="[orange3]running")

            completed = sum(task.completed for task in attacks_progress.tasks)
            overall_progress.update(overall_task, completed=completed)

    table = Table(title=f"Results - {DASHBOARD_URL}/r/test/{test_id}", width=80)
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

    return CliResponse(1 if test_res.get("risk", 100) > risk_threshold else 0)


def run_test_with_json_output(
    access_token: str,
    target: str,
    parallelism: int,
    risk_threshold: int,
    model_wrapper: ModelWrapper,
    submit_test_function: type_submit_test_function,
    modality_specific_args: Optional[BaseModel | None] = None,
) -> CliResponse:

    def _handle_visual_exception_callback(data: str) -> None:
        pass

    # there will be a switch of some kind for this:
    submitted_id = submit_test_function(
        access_token,
        target,
        parallelism,
        model_wrapper,
        _handle_visual_exception_callback,
        modality_specific_args,
    )
    test_id = poll_for_successful_submission(submitted_id)
    test_res = api_service.get_test(access_token=access_token, test_id=test_id)
    while test_res.get("hasFinished", False) is False:
        test_res = api_service.get_test(access_token=access_token, test_id=test_id)
        sleep(API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS)

    print(json.dumps(test_res))
    return CliResponse(1 if test_res.get("risk", 100) > risk_threshold else 0)


# Decorator for authentication, access_token is automatically populated
@require_auth
def cli_run(
    access_token: str,
    json_format: bool,
    risk_threshold: int,
    target: str,
    parallelism: int,
    model_wrapper: ModelWrapper,
    submit_test_function: type_submit_test_function,
    modality_specific_args: Optional[BaseModel | None] = None,
) -> CliResponse:

    if json_format:
        return run_test_with_json_output(
            access_token=access_token,
            risk_threshold=risk_threshold,
            target=target,
            parallelism=parallelism,
            model_wrapper=model_wrapper,
            modality_specific_args=modality_specific_args,
            submit_test_function=submit_test_function,
        )
    else:
        return run_test_with_ui(
            access_token=access_token,
            risk_threshold=risk_threshold,
            target=target,
            parallelism=parallelism,
            model_wrapper=model_wrapper,
            modality_specific_args=modality_specific_args,
            submit_test_function=submit_test_function,
        )
