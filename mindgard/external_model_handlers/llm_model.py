from mindgard.exceptions import handle_exception_callback
from mindgard.exceptions import ErrorCode
from mindgard.types import (
    type_ui_exception_map,
    ExceptionCountTuple,
)

from typing import Optional, Callable, Optional

from rich.progress import Progress


import logging

# Networking
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs
from azure.messaging.webpubsubclient import WebPubSubClient

from mindgard.wrappers.llm import LLMModelWrapper, ContextManager

# Exceptions
from mindgard.exceptions import (
    MGException,
)

def llm_message_handler(
    ui_exception_map: type_ui_exception_map,
    ui_exception_progress: Progress,
    submitted_test_id_update: Callable[[str], None],
    model_wrapper: LLMModelWrapper,
    ws_client: WebPubSubClient,
) -> Callable[[OnGroupDataMessageArgs], None]:
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

    context_manager = ContextManager()

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
                else: # ensure we have access to the eexception trace in debug logging before continuing
                    logging.debug(f"error code: {error_code}", exc_info=True)
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
            submitted_test_id_update(msg.data["payload"]["testId"])
        else:
            pass

    return recv_message_handler
