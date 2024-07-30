import pytest

from ...src.mindgard.webpubsub import (
    WebPubSubMessage,
    wps_network_message_to_mg_message,
)
from pydantic import ValidationError

from ..mocks.webpubsub import ws_client, wait_and_call_factory
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

import time


def test_StartTest_message_model_validation_failure() -> None:
    with pytest.raises(ValidationError):
        WebPubSubMessage(
            messageType="StartTest",
            correlationId=None,
            payload={"something": "nothing"},
        )


def test_StartTest_message_model_validation_success() -> None:
    WebPubSubMessage(
        messageType="StartTest",
        correlationId=None,
        payload={"groupId": "valid_group_id"},
    )


def test_sent_StartTest_message_to_wps() -> None:
    response = ws_client.send_to_group(
        "orchestrator",
        {"messageType": "StartTest", "payload": {"groupId": "valid_group_id"}},
    )
    assert response is None


@pytest.fixture
def StartedTest_message_receieved():  # type: ignore
    return wait_and_call_factory(
        payload={
            "messageType": "StartedTest",
            "payload": {"testId": "valid_test_id"},
        }
    )


def test_received_StartedTest_message_from_wps(StartedTest_message_receieved) -> None:  # type: ignore
    message_received = [False]
    ws_client.subscribe = StartedTest_message_receieved

    def message_handler(message: OnGroupDataMessageArgs) -> None:
        wps_message = wps_network_message_to_mg_message(message)
        assert wps_message.messageType == "StartedTest"
        assert wps_message.payload["testId"] == "valid_test_id"
        message_received[0] = True

    ws_client.subscribe("group-message", message_handler)

    time.sleep(1)
    assert message_received[0]


@pytest.fixture
def Request_message_receieved_valid():  # type: ignore
    return wait_and_call_factory(
        payload={
            "messageType": "Request",
            "correlationId": "valid_correlation_id",
            "payload": {"some": "data"},
        }
    )


def test_received_Request_message_from_wps(Request_message_receieved_valid) -> None:  # type: ignore
    message_received = [False]
    ws_client.subscribe = Request_message_receieved_valid

    def message_handler(message: OnGroupDataMessageArgs) -> None:
        wps_message = wps_network_message_to_mg_message(message)
        assert wps_message.messageType == "Request"
        assert wps_message.payload is not None
        assert wps_message.correlationId == "valid_correlation_id"
        message_received[0] = True

    ws_client.subscribe("group-message", message_handler)

    time.sleep(1)
    assert message_received[0]


@pytest.fixture
def Request_message_receieved_invalid():  # type: ignore
    return wait_and_call_factory(
        payload={
            "messageType": "Request",
            "correlationId": None,
            "payload": {"some": "data"},
        }
    )


def test_received_invalid_Request_message_from_wps(Request_message_receieved_invalid) -> None:  # type: ignore
    message_received = [False]
    ws_client.subscribe = Request_message_receieved_invalid

    def message_handler(message: OnGroupDataMessageArgs) -> None:
        with pytest.raises(ValidationError):
            wps_message = wps_network_message_to_mg_message(message)
            assert wps_message.messageType == "Request"
            assert wps_message.payload is not None
            assert wps_message.correlationId == None
        message_received[0] = True

    ws_client.subscribe("group-message", message_handler)

    time.sleep(1)
    assert message_received[0]
