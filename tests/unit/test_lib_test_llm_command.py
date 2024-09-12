from typing import Any
from unittest.mock import Mock

from azure.messaging.webpubsubclient import WebPubSubClient
import pytest
from mindgard.mindgard_api import AttackResponse, FetchTestDataResponse
from mindgard.test import AttackState, Test, TestConfig, TestImplementationProvider, LLMModelConfig
from mindgard.wrappers.llm import TestStaticResponder

def mock_handler(payload: Any) -> Any:
    return {
        "response": f"hello {payload['prompt']}"
    }

class MockProviderFixture():

    """
    Helper to set up a complete mock provider and access to the mock provider's methods/outputs
    """
    def __init__(self):
        self.test_wps_url = "my test wps url"
        self.test_group_id = "my test group id"
        self.test_id = "my test id"
        self.wps_client = Mock(spec=WebPubSubClient)
        self.provider = Mock(spec=TestImplementationProvider)
        self.provider.init_test.return_value = (self.test_wps_url, self.test_group_id)
        self.provider.create_client.return_value = self.wps_client
        self.provider.start_test.return_value = self.test_id
        self.provider.poll_test.side_effect = [
            None,
            FetchTestDataResponse(
                has_finished=False,
                attacks=[
                    AttackResponse(
                        id="my attack id 1",
                        name="my attack name 1",
                        state="queued"
                    ),
                ]
            ),
            FetchTestDataResponse(
                has_finished=True,
                attacks=[
                    AttackResponse(
                        id="my attack id 1",
                        name="my attack name 1",
                        state="completed",
                        errored=False,
                        risk=45,
                    ),
                    AttackResponse(
                        id="my attack id 2",
                        name="my attack name 2",
                        state="completed",
                        errored=True,
                        risk=45,
                    ),
                ]
            )
        ]

@pytest.fixture
def mock_provider():
    return MockProviderFixture()

@pytest.fixture
def config():
    return TestConfig(
        api_base="your_api_base",
        api_access_token="your_api_access_token",
        target="your_target",
        attack_source="your_attack_source",
        parallelism=1,
        model=LLMModelConfig(
            wrapper=TestStaticResponder(system_prompt="test",handler=mock_handler),
            system_prompt="your_system_prompt",
            model_type="your_model_type"
        )
    )

def test_lib_runs_test_complete(mock_provider:MockProviderFixture, config:TestConfig):
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # TODO: fixme
    test.run()

    mock_provider.provider.init_test.assert_called_once_with(config)
    mock_provider.provider.create_client.assert_called_once_with(mock_provider.test_wps_url)
    mock_provider.provider.connect_websocket.assert_called_once_with(mock_provider.wps_client)
    mock_provider.provider.register_handler.assert_called_once_with(mock_handler, mock_provider.wps_client, mock_provider.test_group_id)
    mock_provider.provider.start_test.assert_called_once_with(mock_provider.wps_client, mock_provider.test_group_id)
    mock_provider.provider.close.assert_called_once_with(mock_provider.wps_client)

    assert (state := test.get_state()) is not None, "the test should have a state"
    assert state.test_complete == True, "the test should be completed"
    assert len(state.attacks) == 2, "the test should have 2 attacks"
    assert state.attacks[0].name == "my attack name 1", "the attack name should be correct"
    assert state.attacks[0].state == "completed", "the attack state should be completed"
    assert state.attacks[0].errored == False, "the attack should not be errored"
    assert state.attacks[0].risk == 45, "the attack risk should be correct"

    assert state.attacks[1].errored == True, "the attack should be errored"
    assert state.attacks[1].risk == None, "the attack risk should None for errored attacks"

def test_lib_does_not_expose_writable_state(config:TestConfig):
    test = Test(config)
    before_state = test.get_state()
    assert before_state.model_exceptions == [], "the model exceptions should be empty at start (for validity of test)"
     # mutate the state (copy)
    before_state.model_exceptions.append(Exception("mytest"))
    before_state.attacks.append(AttackState(id="myattack", name="myattack", state="queued"))
    assert test.get_state().model_exceptions == [], "the state should not be writable externally"

def test_lib_closes_on_exception(mock_provider:MockProviderFixture, config:TestConfig):
    """
    Unrecovered failures during execution should not leave the test running.
    Exception should be propagated to the caller unaltered (this is unhandled case).
    """
    exception = Exception("test exception")
    mock_provider.provider.poll_test.side_effect = exception

    with pytest.raises(Exception) as e:
        test = Test(config)
        test._provider = mock_provider.provider # TODO: fixme
        test.run()
    assert e.value == exception, "the same exception should be propagated (not a copy/wrap)"
    assert mock_provider.provider.close.called, "the test should be closed even if an exception is raised"
