from ..run_poll_display import type_ui_exception_map

from typing import Callable, List

from ..wrappers.image import ImageModelWrapper

from rich.progress import Progress

from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs
from azure.messaging.webpubsubclient import WebPubSubClient

import base64

import logging


def image_message_handler(
    ui_exception_map: type_ui_exception_map,
    ui_exception_progress: Progress,
    submitted_test_id_update: Callable[[str], None],
    model_wrapper: ImageModelWrapper,
    ws_client: WebPubSubClient,
) -> Callable[[OnGroupDataMessageArgs], None]:
    def recv_message_handler(msg: OnGroupDataMessageArgs) -> None:
        if msg.data["messageType"] == "Request":
            logging.debug(f"received request {msg.data=}")
            image_bytes = base64.b64decode(msg.data["payload"]["image"])

            try:
                response = model_wrapper.__call__(image=image_bytes)
            except Exception as e:
                raise e
            finally:
                # we always try to send a response
                replyData = {
                    "correlationId": msg.data["correlationId"],
                    "messageType": "Response",
                    "status": "ok",  # Deprecated but kept for compatibility
                    "payload": {"response": [t.model_dump() for t in response]},
                }
                logging.debug(f"sending response {replyData=}")

                ws_client.send_to_group("orchestrator", replyData, data_type="json")  # type: ignore
        elif msg.data["messageType"] == "StartedTest":
            submitted_test_id_update(msg.data["payload"]["testId"])
        else:
            pass

    return recv_message_handler
