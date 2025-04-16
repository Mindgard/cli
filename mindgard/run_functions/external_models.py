from mindgard.wrappers.llm import LLMModelWrapper
from ..orchestrator import (
    setup_orchestrator_webpubsub_request,
    OrchestratorSetupRequest,
    OrchestratorTestResponse,
    get_test_by_id, GetTestAttacksResponse,
)
from ..types import (
    type_ui_task_map,
    type_output_func,
    type_submit_func,
    type_ui_exception_map,
)
from ..ui_prefabs import poll_and_display_test, output_test_table

from typing import Optional, List, Callable, Union
from rich.progress import Progress
from rich.table import Table

from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

import time


def model_test_submit_factory(
    request: OrchestratorSetupRequest,
    model_wrapper: LLMModelWrapper,
    message_handler: Callable[
        [
            type_ui_exception_map,
            Progress,
            Callable[[str], None],
            LLMModelWrapper,
            WebPubSubClient,
        ],
        Callable[[OnGroupDataMessageArgs], None],
    ],
) -> type_submit_func:

    def model_test_submit(
        access_token: str,
        ui_exception_map: type_ui_exception_map,
        ui_exception_progress: Progress,
    ) -> GetTestAttacksResponse:
        
        response = setup_orchestrator_webpubsub_request(
            access_token=access_token, request=request
        )

        credentials = WebPubSubClientCredential(client_access_url_provider=response.url)
        ws_client = WebPubSubClient(credential=credentials)

        submitted_test_id = [""]

        def update_submited_test_id(id: str) -> None:
            submitted_test_id[0] = id

        recv_message_handler = message_handler(
            ui_exception_map,
            ui_exception_progress,
            update_submited_test_id,
            model_wrapper,
            ws_client,
        )

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
        while submitted_test_id[0] == "":
            time.sleep(1)
            attempts_remaining -= 1
            if attempts_remaining == 0:
                break

        # we're here if submitting was a success...

        if attempts_remaining != 0 and submitted_test_id[0] != "":
            return get_test_by_id(
                test_id=submitted_test_id[0], access_token=access_token
            )
        else:
            raise Exception(
                f"did not receive notification of test submitted within timeout ({max_attempts}s); failed to start test"
            )

    return model_test_submit


def model_test_polling(
    access_token: str,
    initial_test: GetTestAttacksResponse,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
) -> Optional[GetTestAttacksResponse]:
    return poll_and_display_test(
        access_token,
        ui_task_map,
        ui_task_progress,
        initial_test,
    )


def model_test_output_factory(risk_threshold: int) -> type_output_func:
    def list_llm_test_output(
        test: GetTestAttacksResponse, json_out: bool
    ) -> Optional[Table]:
        return output_test_table(
            json_out=json_out, test=test, risk_threshold=risk_threshold
        )

    return list_llm_test_output
