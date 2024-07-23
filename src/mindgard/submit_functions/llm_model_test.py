from ..run_poll_display import (
    type_submit_func,
    type_polling_func,
    type_output_func,
    type_ui_task_map,
    type_ui_exception_map,
    ExceptionCountTuple,
)

from typing import Optional, Callable, Literal, List, Optional, Dict, Type

from ..utils import print_to_stderr_as_json

from ..orchestrator import (
    setup_orchestrator_webpubsub_request,
    OrchestratorSetupRequest,
    OrchestratorTestResponse,
    get_test_by_id,
)

from rich.progress import Progress

from ..constants import DASHBOARD_URL

import time

import json

import logging

# Networking
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

from ..wrappers import ModelWrapper, ContextManager

from rich.table import Table

# Exceptions
from ..exceptions import (
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
    NotImplemented,
)

ErrorCode = Literal[
    "CouldNotContact",
    "ContentPolicy",
    "CLIError",
    "NotImplemented",
    "NoResponse",
    "RateLimited",
    "NetworkIssue",
    "MaxContextLength",
]

exceptions_to_cli_status_codes: Dict[Type[Exception], ErrorCode] = {
    Uncontactable: "CouldNotContact",
    BadRequest: "NoResponse",  # not sure about this, we don't handle 400 atm
    Unauthorized: "NoResponse",
    Forbidden: "NoResponse",
    NotFound: "NoResponse",
    Timeout: "NoResponse",
    UnprocessableEntity: "NoResponse",  # this is currently being handled as a rate limit issue for some reason
    FailedDependency: "NoResponse",
    RateLimitOrInsufficientCredits: "RateLimited",
    InternalServerError: "NoResponse",
    ServiceUnavailable: "NoResponse",
    NotImplemented: "NotImplemented",
    EmptyResponse: "NoResponse",
}


def handle_exception_callback(
    exception: Exception,
    handle_visual_exception_callback: Optional[Callable[[str], None]],
) -> ErrorCode:
    # TODO - come take a look at this
    error_code: ErrorCode = exceptions_to_cli_status_codes.get(type(exception), "CLIError")  # type: ignore
    callback_text = str(exception)

    if handle_visual_exception_callback:
        handle_visual_exception_callback(callback_text)

    logging.debug(exception)
    return error_code


def llm_test_submit_factory(
    target: str, parallelism: int, model_wrapper: ModelWrapper, system_prompt: str
) -> type_submit_func:

    def llm_test_submit(
        access_token: str,
        ui_exception_map: type_ui_exception_map,
        ui_exception_progress: Progress,
    ) -> OrchestratorTestResponse:

        request = OrchestratorSetupRequest(
            target=target,
            model_type="llm",
            system_prompt=system_prompt,
            attackSource="user",
            parallelism=parallelism,
        )

        response = setup_orchestrator_webpubsub_request(
            access_token=access_token, request=request
        )

        credentials = WebPubSubClientCredential(client_access_url_provider=response.url)
        ws_client = WebPubSubClient(credential=credentials)

        context_manager = ContextManager()

        submitted_test_id: List[Optional[str]] = [None]

        def _handle_visual_exception_callback(text: str) -> None:
            if not ui_exception_map.get(text, None):
                ui_exception_map[text] = ExceptionCountTuple(
                    ui_exception_progress.add_task(""), 0
                )

            ui_exception_map[text].count += 1
            ui_exception_progress.update(
                ui_exception_map[text].task_id,
                description=f"[dark_orange3][!!!] {text} (x{ui_exception_map[text].count})",
            )

        def temp_handler(e: Exception) -> ErrorCode:
            return handle_exception_callback(e, _handle_visual_exception_callback)

        # this guy is difficult to manage exceptions for as websocket messages are event-based.
        # the recv message handler also has no idea which messages are for which attack, so
        # we can't mark an attack as failed until we are complete
        def recv_message_handler(msg: OnGroupDataMessageArgs) -> None:
            if msg.data["messageType"] == "Request":
                logging.debug(f"received request {msg.data=}")
                context_id = msg.data["payload"].get("context_id", None)
                context = context_manager.get_context_or_none(context_id)
                content = msg.data["payload"]["prompt"]

                response: str = ""
                error_code: Optional[ErrorCode] = None

                try:
                    # would pose being explicit with __call__ so we can ctrl+f easier, not a very clear shorthand
                    response = model_wrapper.__call__(
                        content=content,
                        with_context=context,
                    )
                except MGException as mge:
                    error_code = temp_handler(mge)
                    if error_code == "CLIError":
                        raise mge
                except Exception as e:
                    raise e
                finally:
                    # we always try to send a response
                    replyData = {
                        "correlationId": msg.data["correlationId"],
                        "messageType": "Response",
                        "status": "ok",  # Deprecated but kept for compatibility
                        "payload": {
                            "response": response,
                            "error": error_code,
                        },
                    }
                    logging.debug(f"sending response {replyData=}")

                    ws_client.send_to_group("orchestrator", replyData, data_type="json")  # type: ignore
            elif (
                msg.data["messageType"] == "StartedTest"
            ):  # should be something like "Submitted", upstream change required.
                submitted_test_id[0] = msg.data["payload"]["testId"]
            else:
                pass

        ws_client.open()

        ws_client.subscribe("group-message", recv_message_handler)  # type: ignore

        payload = {
            "correlationId": "",
            "messageType": "StartTest",
            "payload": {"groupId": response.group_id},
        }

        ws_client.send_to_group(group_name="orchestrator", content=payload, data_type="json")  # type: ignore

        # wait
        max_attempts = 30
        attempts_remaining = max_attempts
        while submitted_test_id[0] is None:
            time.sleep(1)
            attempts_remaining -= 1
            if attempts_remaining == 0:
                break

        # we're here if submitting was a success...

        if attempts_remaining != 0 and submitted_test_id[0] is not None:
            return get_test_by_id(
                test_id=submitted_test_id[0], access_token=access_token
            )
        else:
            raise Exception(
                f"did not receive notification of test submitted within timeout ({max_attempts}s); failed to start test"
            )

    return llm_test_submit


def poll_and_display_test(
    access_token: str,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
    initial_test: OrchestratorTestResponse,
) -> Optional[OrchestratorTestResponse]:
    test = get_test_by_id(access_token=access_token, test_id=initial_test.id)

    if len(ui_task_map.keys()) == 0:
        for attack in test.attacks:
            ui_task_map[attack.id] = ui_task_progress.add_task(
                f"Attack {attack.attack}", total=1, status="[chartreuse1]queued"
            )

    for attack in test.attacks:
        task_id = ui_task_map[attack.id]
        if attack.state == 2:
            ui_task_progress.update(task_id, completed=1, status="[chartreuse3]success")
        elif attack.state == -1:
            ui_task_progress.update(task_id, completed=1, status="[red3]failed")
        elif attack.state == 1:
            ui_task_progress.update(task_id, status="[orange3]running")

    if test.hasFinished is False:
        return None
    return test


def llm_test_polling(
    access_token: str,
    initial_test: OrchestratorTestResponse,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
) -> Optional[OrchestratorTestResponse]:
    return poll_and_display_test(
        access_token,
        ui_task_map,
        ui_task_progress,
        initial_test,
    )


def output_test_table(
    json_out: bool,
    test: OrchestratorTestResponse,
    risk_threshold: int,
) -> Optional[Table]:
    if json_out:
        print_to_stderr_as_json(test.model_dump())
        return None
    else:
        table = Table(title=f"Results - {DASHBOARD_URL}/r/test/{test.id}", width=80)
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Risk", justify="right", style="green")

        for attack in test.attacks:
            if attack.state != 2:
                name = f"Error running '{attack.attack}'"
                risk_str = "n/a"
                emoji = "❗️"
            else:
                name = attack.attack
                risk_str = str(attack.risk)
                emoji = "❌‍" if attack.risk > risk_threshold else "✅️"

            table.add_row(emoji, name, risk_str)

        return table


def llm_test_output_factory(risk_threshold: int) -> type_output_func:
    def list_llm_test_output(
        test: OrchestratorTestResponse, json_out: bool
    ) -> Optional[Table]:
        return output_test_table(
            json_out=json_out, test=test, risk_threshold=risk_threshold
        )

    return list_llm_test_output
