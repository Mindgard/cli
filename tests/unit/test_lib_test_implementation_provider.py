
# the system under test here is a series of blocking calls that
# primarily interact with external services. As such we will have
# test doubles to simulate those interactions.

from typing import Any, Callable, Dict, List, Literal, Optional
from unittest import mock

import pytest
import requests_mock
from mindgard.mindgard_api import MindgardApi
from mindgard.version import VERSION
from mindgard.test import InternalError, TestConfig, TestImplementationProvider, LLMModelConfig, UnauthorizedError
from mindgard.wrappers.llm import Context, LLMModelWrapper, PromptResponse

from azure.messaging.webpubsubclient import WebPubSubClient
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, CallbackType, WebPubSubDataType


# Please there must be a better way to get pytest to ignore these


# TODO: move to test utils
class MockModelWrapper(LLMModelWrapper):
    """
    A mock model wrapper that mirrors the input prepending with 'hello {input}'
    
    If a context is provided, it will also append the number of turns in the context: 'hello {input} {n}'
    """
    @classmethod
    def mirror(cls, input:str) -> str:
        return "hello " + input
    
    def __call__(self, content:str, with_context:Optional[Context] = None) -> PromptResponse:
        if with_context:
            res = self.mirror(content) + " " + str(len(with_context.turns))
            prompt_response = PromptResponse(prompt=content, response=res, duration_ms=1)
            with_context.add(prompt_response)
            return prompt_response

        mirrored_content = self.mirror(content)
        return PromptResponse(prompt=content, response=mirrored_content, duration_ms=1)

def _helper_default_config(extra: Dict[str, Any] = {}) -> TestConfig:
    return TestConfig(
        api_base="https://test.internal",
        api_access_token="my access token",
        target = "my target",
        attack_pack = "my attack pack",
        attack_source = "my attack source",
        parallelism = 3,
        model = LLMModelConfig(
            wrapper=MockModelWrapper(),
            system_prompt = "my system prompt"
        ),
        **extra
    )

def test_init_test(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    test_url = "test_url"
    test_group_id = "test_group_id"

    # inputs
    config = _helper_default_config()
    test_api_base = "https://test.internal"
    test_access_token = "my access token"
    
    cli_init_requests = requests_mock.post(
        f"{test_api_base}/tests/cli_init",
        json={
            "url": test_url,
            "groupId": test_group_id
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    url, group_id = provider.init_test(config)

    assert url == test_url
    assert group_id == test_group_id
    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.headers.get("Authorization") == f"Bearer {test_access_token}", "should set authorization header"
    assert cli_init_requests.last_request.headers.get("X-User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert cli_init_requests.last_request.headers.get("User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert cli_init_requests.last_request.json() == {
        "target": config.target,
        "modelType": config.model.model_type,
        "system_prompt": config.model.system_prompt,
        "attackPack": config.attack_pack,
        "parallelism": config.parallelism,
        "attackSource": config.attack_source,
        "attackPack": config.attack_pack
    }

def test_init_test_with_target_id(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    target_id = "my target id"

    # inputs
    config = _helper_default_config()
    config.target_id = target_id
    
    cli_init_requests = requests_mock.post(
        "https://test.internal/tests/cli_init",
        json={
            "url": "test_url",
            "groupId": "test_group_id"
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    provider.init_test(config)

    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.json().get("target_id") == target_id

def test_init_test_with_domain(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    dataset_domain = 'some_arbitary_string'

    # inputs
    config = _helper_default_config({'dataset_domain': dataset_domain})
    test_api_base = "https://test.internal"
    
    cli_init_requests = requests_mock.post(
        f"{test_api_base}/tests/cli_init",
        json={
            "url": 'url',
            "groupId": 'groupid'
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    provider.init_test(config)

    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.json().get('datasetDomain') == dataset_domain


def test_init_test_with_exclude(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    exclude = ['AntiGPT', 'PersonGPT']

    # inputs
    config = _helper_default_config({'exclude': exclude})
    test_api_base = "https://test.internal"
    
    cli_init_requests = requests_mock.post(
        f"{test_api_base}/tests/cli_init",
        json={
            "url": 'url',
            "groupId": 'groupid'
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    provider.init_test(config)

    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.json().get('exclude') == exclude



def test_init_test_with_include(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    include = ['AntiGPT', 'PersonGPT']

    # inputs
    config = _helper_default_config({'include': include})
    test_api_base = "https://test.internal"
    
    cli_init_requests = requests_mock.post(
        f"{test_api_base}/tests/cli_init",
        json={
            "url": 'url',
            "groupId": 'groupid'
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    provider.init_test(config)

    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.json().get('include') == include



def test_init_test_with_include_and_exclude(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    include = ['AntiGPT', 'PersonGPT']
    exclude = ['base64', 'base32']

    # inputs
    config = _helper_default_config({'include': include, 'exclude': exclude})
    test_api_base = "https://test.internal"
    
    cli_init_requests = requests_mock.post(
        f"{test_api_base}/tests/cli_init",
        json={
            "url": 'url',
            "groupId": 'groupid'
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    provider.init_test(config)

    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.json().get('exclude') == exclude
    assert cli_init_requests.last_request.json().get('include') == include



def test_init_test_using_api_key_auth_flow(requests_mock: requests_mock.Mocker) -> None:
    # expectations
    test_url = "test_url"
    test_group_id = "test_group_id"

    additional_headers = {
        "x-api-key": "my-api-key",
        "x-associated-user-sub": "my-user-sub"
    }

    # inputs
    config = _helper_default_config(extra={"additional_headers": additional_headers})
    test_api_base = "https://test.internal"
    test_access_token = "my access token"
    
    cli_init_requests = requests_mock.post(
        f"{test_api_base}/tests/cli_init",
        json={
            "url": test_url,
            "groupId": test_group_id
        },
        status_code=200,
    )

    # test
    provider = TestImplementationProvider()
    url, group_id = provider.init_test(config)

    assert url == test_url
    assert group_id == test_group_id
    assert cli_init_requests.call_count == 1
    assert cli_init_requests.last_request is not None
    assert cli_init_requests.last_request.headers.get("Authorization") == f"Bearer {test_access_token}", "should set authorization header"
    assert cli_init_requests.last_request.headers.get("X-User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert cli_init_requests.last_request.headers.get("User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert cli_init_requests.last_request.headers.get("x-api-key") == additional_headers.get("x-api-key"), "should set additional headers"
    assert cli_init_requests.last_request.headers.get("x-associated-user-sub") == additional_headers.get("x-associated-user-sub"), "should set additional headers"
    assert cli_init_requests.last_request.json() == {
        "target": config.target,
        "modelType": config.model.model_type,
        "system_prompt": config.model.system_prompt,
        "attackPack": config.attack_pack,
        "parallelism": config.parallelism,
        "attackSource": config.attack_source,
        "attackPack": config.attack_pack,
    }

def test_init_test_unauthorized(requests_mock: requests_mock.Mocker) -> None:
    test_url = "test_url"
    test_group_id = "test_group_id"
    for code in [401, 403]:
        # inputs
        config = _helper_default_config()
        
        requests_mock.post(
            f"{config.api_base}/tests/cli_init",
            json={
                "url": test_url,
                "groupId": test_group_id
            },
            status_code=code,
        )
        provider = TestImplementationProvider()

        with pytest.raises(UnauthorizedError):
            provider.init_test(config)

        # TODO: assert __cause__ (e.value.__cause__)

def test_init_test_unknown_error(requests_mock: requests_mock.Mocker) -> None:
    test_url = "test_url"
    test_group_id = "test_group_id"
    for code in [500, 501, 502]:
        # inputs
        config = _helper_default_config()
        
        requests_mock.post(
            f"{config.api_base}/tests/cli_init",
            json={
                "url": test_url,
                "groupId": test_group_id
            },
            status_code=code,
        )
        provider = TestImplementationProvider()

        with pytest.raises(InternalError):
            provider.init_test(config)

        # TODO: assert __cause__ (e.value.__cause__)

@mock.patch("mindgard.test.WebPubSubClientCredential", autospec=True)
@mock.patch("mindgard.test.WebPubSubClient", autospec=True)
def test_create_websocket_client(mock_wps_client: mock.MagicMock, mock_wps_client_credential: mock.MagicMock) -> None:
    mock_wps_client_credential.return_value = {"something":"a"} # don't care what for now
    
    mock_client = mock.MagicMock(spec=WebPubSubClient)
    mock_wps_client.return_value = mock_client

    test_connection_url = "test_connection_url"
    provider = TestImplementationProvider()
    client = provider.create_client(test_connection_url)

    mock_wps_client_credential.assert_called_once_with(client_access_url_provider=test_connection_url)
    mock_wps_client.assert_called_once_with(credential=mock_wps_client_credential.return_value)
    assert client == mock_client

def test_connect_websocket() -> None:    
    mock_client = mock.MagicMock(spec=WebPubSubClient)

    provider = TestImplementationProvider()
    provider.connect_websocket(mock_client)

    mock_client.open.assert_called_once()

def test_wrapper_to_handler() -> None:
    wrapper = MockModelWrapper()
    handler = wrapper.to_handler()
    request_payload = {"prompt": "world"}

    response_payload = handler(request_payload)
    assert response_payload['response'] == "hello world", "should return a response"
    assert response_payload['duration_ms'] == 1, "should return a duration in milliseconds from the MockModelWrapper"

def test_wrapper_to_handler_with_context() -> None:
    wrapper = MockModelWrapper()
    handler = wrapper.to_handler()
    request_payload = {"prompt": "world", "context_id": "mycontext"}

    response_payload_0 = handler(request_payload)
    assert response_payload_0['response'] == "hello world 0", "should return a response"
    assert response_payload_0['duration_ms'] == 1, "should return a duration in milliseconds from the MockModelWrapper"

    response_payload_1 = handler(request_payload)
    assert response_payload_1['response'] == "hello world 1", "should return a response"
    assert response_payload_1['duration_ms'] == 1, "should return a duration in milliseconds from the MockModelWrapper"

def test_register_handler() -> None:
    has_handler: List[Callable[[OnGroupDataMessageArgs], None]] = []
    has_sent_to_group: List[Dict[str, Any]] = []
    def subscribe(group_name:str, handler:Callable[[OnGroupDataMessageArgs], None]) -> None:
        assert group_name == CallbackType.GROUP_MESSAGE
        assert handler is not None
        has_handler.append(handler)

    def mock_send_to_group(
        group_name: str,
        content: Dict[str, Any],
        data_type: Literal[WebPubSubDataType.JSON]
    ) -> None:
        assert group_name == "orchestrator", "Responses should be sent to the orchestrator group"
        assert data_type == WebPubSubDataType.JSON, "Responses' data type should be JSON"
        has_sent_to_group.append(content)
        
    mock_wps_client = mock.MagicMock(spec=WebPubSubClient)
    mock_wps_client.subscribe = subscribe
    mock_wps_client.send_to_group = mock_send_to_group

    group_id = "test_group_id"
    def mock_handler(payload: Any) -> Any:
        return {
            "response": f"hello {payload['prompt']}",
            "duration_ms": 2
        }
    provider = TestImplementationProvider()

    provider.register_handler(mock_handler, mock_wps_client, group_id)

    assert has_handler[0] is not None
    handler = has_handler[0]

    # send a message
    msg = OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "id1", "messageType": "Request", "payload": {"prompt": "world"}})
    handler(msg)

    assert len(has_sent_to_group) == 1, "Request messages should be responded to"
    assert has_sent_to_group[0]["correlationId"] == "id1", "should echo the correlation id"
    assert has_sent_to_group[0]["messageType"] == "Response", "should be a Response messageType"
    assert has_sent_to_group[0]["status"] == "ok", "should be an ok status"
    assert has_sent_to_group[0]["payload"]["response"] == "hello world", "should return the correct response payload"
    assert has_sent_to_group[0]["payload"]["duration_ms"] == 2, "should return the duration in milliseconds"

    # incorrect message type
    msg = OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "id1", "messageType": "NotRequest", "payload": {"prompt": "world"}})
    handler(msg)

    assert len(has_sent_to_group) == 1, "Non Request messages should be ignored"

def test_start_test() -> None:
    want_group_id = "my group id"
    want_test_id = "my test id"
    
    # TODO fix test code duplication from above
    has_handler: List[Callable[[OnGroupDataMessageArgs], None]] = []
    def subscribe(group_name:str, handler:Callable[[OnGroupDataMessageArgs], None]) -> None:
        assert group_name == CallbackType.GROUP_MESSAGE
        assert handler is not None
        has_handler.append(handler)

    def mock_send_to_group(
        group_name: str,
        content: Dict[str, Any],
        data_type: Literal[WebPubSubDataType.JSON]
    ) -> None:
        assert group_name == "orchestrator", "Responses should be sent to the orchestrator group"
        assert data_type == WebPubSubDataType.JSON, "Responses' data type should be JSON"
        assert content == {
            "correlationId": "",
            "messageType": "StartTest",
            "payload": {"groupId": want_group_id},
        }, "test should be started with correct payload"
        assert len(has_handler) == 1, "handler should be set by the time the test is started"
        has_handler[0](
            OnGroupDataMessageArgs(
                group=want_group_id, 
                data_type=WebPubSubDataType.JSON, 
                data={
                    "messageType": "StartedTest", 
                    "payload": {"testId": want_test_id}
                }
            )
        )
        
    mock_wps_client = mock.MagicMock(spec=WebPubSubClient)
    mock_wps_client.subscribe = subscribe
    mock_wps_client.send_to_group = mock_send_to_group

    provider = TestImplementationProvider()
    test_id = provider.start_test(mock_wps_client, want_group_id)

    assert test_id == want_test_id, "should return the correct test id"

def test_start_test_timeout() -> None:
    group_id = "my group id"
    mock_wps_client = mock.MagicMock(spec=WebPubSubClient)
    provider = TestImplementationProvider()
    with pytest.raises(InternalError, match="Failure: timeout waiting for test to start"):
        provider.start_test(mock_wps_client, group_id, 0)

def test_poll_test_returns_using_api_token_auth_flow() -> None:
    mock_mindgard_api = mock.MagicMock(spec=MindgardApi)

    test_id = "my test id"
    additional_headers = {
        "x-api-key": "my-api-key",
        "x-associated-user-sub": "my-user-sub"
    }
    config = _helper_default_config(extra={"additional_headers": additional_headers})

    # test
    provider = TestImplementationProvider(mock_mindgard_api)
    ret = provider.poll_test(config, test_id)
    assert ret == mock_mindgard_api.fetch_test_attacks.return_value, "should return the result of the fetch_test_data call"
    mock_mindgard_api.fetch_test_attacks.assert_called_once_with(
        api_base="https://test.internal", 
        access_token="my access token", 
        additional_headers=additional_headers, 
        test_id=test_id
    )

def test_poll_test_bubbles_up_exceptions() -> None:
    mock_mindgard_api = mock.MagicMock(spec=MindgardApi)

    test_id = "my test id"
    config = _helper_default_config()

    # test
    provider = TestImplementationProvider(mock_mindgard_api)
    mock_mindgard_api.fetch_test_attacks.side_effect = ValueError("test error")
    with pytest.raises(InternalError):
        provider.poll_test(config, test_id)

def test_close() -> None:
    wps_client = mock.MagicMock(spec=WebPubSubClient)
    provider = TestImplementationProvider()
    provider.close(wps_client)
    wps_client.close.assert_called_once()