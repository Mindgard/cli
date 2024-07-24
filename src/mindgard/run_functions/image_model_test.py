from ..run_poll_display import type_submit_func, type_ui_exception_map

from ..orchestrator import (
    OrchestratorTestResponse,
)

from typing import List, Optional

from ..wrappers.image import ImageModelWrapper

from rich.progress import Progress

from ..orchestrator import (
    OrchestratorTestResponse,
    setup_orchestrator_webpubsub_request,
    OrchestratorSetupRequest,
    get_test_by_id,
)

from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

import base64

import logging

import time


def image_test_submit_factory(
    target: str, parallelism: int, dataset: str, model_wrapper: ImageModelWrapper
) -> type_submit_func:

    def image_test_submit(
        access_token: str,
        ui_exception_map: type_ui_exception_map,
        ui_exception_progress: Progress,
    ) -> OrchestratorTestResponse:
        request = OrchestratorSetupRequest(
            target=target,
            modelType="image",
            attackSource="user",
            dataset=dataset,
            parallelism=parallelism,
        )

        response = setup_orchestrator_webpubsub_request(
            access_token=access_token, request=request
        )

        credentials = WebPubSubClientCredential(client_access_url_provider=response.url)
        ws_client = WebPubSubClient(credential=credentials)

        submitted_test_id: List[Optional[str]] = [None]

        # this guy is difficult to manage exceptions for as websocket messages are event-based.
        # the recv message handler also has no idea which messages are for which attack, so
        # we can't mark an attack as failed until we are complete
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

    return image_test_submit
