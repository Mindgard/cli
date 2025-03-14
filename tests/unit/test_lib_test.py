from typing import Any, Dict
from unittest.mock import ANY, Mock

from azure.messaging.webpubsubclient import WebPubSubClient
import pytest
from mindgard.constants import DEFAULT_RISK_THRESHOLD
from mindgard.mindgard_api import AttackResponse, FetchTestDataResponse
from mindgard.test import AttackState, InternalError, RequestHandler, Test, TestConfig, TestImplementationProvider, LLMModelConfig, UnauthorizedError
from mindgard.wrappers.llm import TestStaticResponder
from tests.unit.test_test_llm_command import PropagatingThread

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
                risk=0,
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
                risk=44,
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

def test_lib_error_handling(mock_provider:MockProviderFixture, config:TestConfig):
    def mock_register_handler(handler: RequestHandler, client:str, group_id:str):
        handler({
            "anything":"is ok"
        })

    want_exception = Exception("something")
    class MockWrapper():
        def to_handler(self) -> RequestHandler:
            def handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                raise want_exception
            return handler

    mock_provider.provider.register_handler.side_effect = mock_register_handler
    test = Test(config, poll_period_seconds=0)
    config.model.wrapper = MockWrapper()

    test._provider = mock_provider.provider # type: ignore # TODO: fixme

    test.run()
    state = test.get_state()
    assert len(state.model_exceptions), "the state should show the singular exception"
    assert str(state.model_exceptions[0]) == str(want_exception), "the exception in state should match the raised exception"

def test_lib_runs_test_complete(mock_provider:MockProviderFixture, config:TestConfig):
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
    test.run()

    mock_provider.provider.init_test.assert_called_once_with(config)
    mock_provider.provider.create_client.assert_called_once_with(mock_provider.test_wps_url)
    mock_provider.provider.connect_websocket.assert_called_once_with(mock_provider.wps_client)
    
    # when the exception handling is fixed, we should assert that the handler is provided
    #       for now we can assert that the handler looks like it should (out mock fixture)
    mock_provider.provider.register_handler.assert_called_once_with(ANY, mock_provider.wps_client, mock_provider.test_group_id)
    payload_in = {"prompt":"is ok"}
    assert mock_provider.provider.register_handler.call_args[0][0](payload_in) == mock_handler(payload_in), "the handler should be the one provided"

    mock_provider.provider.start_test.assert_called_once_with(mock_provider.wps_client, mock_provider.test_group_id)
    mock_provider.provider.close.assert_called_once_with(mock_provider.wps_client)

    assert (state := test.get_state()) is not None, "the test should have a state"
    assert state.test_complete == True, "the test should be completed"

def test_lib_does_not_expose_writable_state(config:TestConfig):
    test = Test(config)
    before_state = test.get_state()
    assert before_state.model_exceptions == [], "the model exceptions should be empty at start (for validity of test)"
     # mutate the state (copy)
    before_state.model_exceptions.append("mytest")
    before_state.attacks.append(AttackState(id="myattack", name="myattack", state="queued"))
    assert test.get_state().model_exceptions == [], "the state should not be writable externally"

def test_lib_closes_on_exception(mock_provider:MockProviderFixture, config:TestConfig):
    """
    Unrecovered failures during execution should not leave the test running.
    Exception should be propagated to the caller unaltered (this is unhandled case).
    """
    exception = Exception("test exception")
    mock_provider.provider.init_test.side_effect = exception

    with pytest.raises(InternalError) as e:
        test = Test(config)
        test._provider = mock_provider.provider # type: ignore # TODO: fixme
        test.run()
    assert e.value.__cause__ == exception, "the same exception should be propagated (not a copy/wrap)"
    assert mock_provider.provider.close.called, "the test should be closed even if an exception is raised"

def test_test_config_defaults():
    got_config = TestConfig(
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
    
    assert got_config.risk_threshold == DEFAULT_RISK_THRESHOLD, f"the default risk threshold should be {DEFAULT_RISK_THRESHOLD=}"
    assert got_config.attack_pack == "sandbox", "the default attack pack should be sandbox"
    assert got_config.additional_headers == None, "the default additional_headers should be empty"

def test_lib_raises_in_state_wait_for(mock_provider:MockProviderFixture, config:TestConfig):
    mock_provider.provider.poll_test.side_effect = UnauthorizedError()
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
            
    test_run = PropagatingThread(target=test.run)
    test_run.start()

    with pytest.raises(UnauthorizedError):
        with test.state_wait_for(lambda state: state.test_complete):
            pass

    with pytest.raises(UnauthorizedError):
        test_run.join()
    
def test_lib_raises_in_state_wait(mock_provider:MockProviderFixture, config:TestConfig):
    mock_provider.provider.poll_test.side_effect = UnauthorizedError()
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
            
    test_run = PropagatingThread(target=test.run)
    test_run.start()

    with pytest.raises(UnauthorizedError):
        while True: 
            with test.state_wait() as state:
                # mediocre attempt to stop test blocking forever
                if state.test_complete:
                    break

    with pytest.raises(UnauthorizedError):
        test_run.join()

def test_lib_raises_in_state_then_wait_if(mock_provider:MockProviderFixture, config:TestConfig):
    mock_provider.provider.init_test.side_effect = UnauthorizedError()
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
            
    test_run = PropagatingThread(target=test.run)
    test_run.start()

    with pytest.raises(UnauthorizedError):
        with test.state_then_wait_if(lambda state: state.test_complete):
            pass

    with pytest.raises(UnauthorizedError):
        test_run.join()

def test_lib_raises_internal_error(mock_provider:MockProviderFixture, config:TestConfig):
    expect_exception_inner = Exception("this is the cause")
    mock_provider.provider.poll_test.side_effect = expect_exception_inner
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme

    with pytest.raises(InternalError) as e:
        test.run()

    assert e.value.__cause__ is expect_exception_inner, "the InternalError's cause should be the original exception"

# TODO: hurriedly added this test, but the exception handling is not well designed yet
def test_lib_retries_9_times(mock_provider:MockProviderFixture, config:TestConfig):
    mock_provider.provider.poll_test.side_effect = [UnauthorizedError()] * 9 + [FetchTestDataResponse(has_finished=True, risk=0, attacks=[])]
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
    
    test.run()
    assert test.get_state().test_complete == True, "the test should be completed"

# TODO: hurriedly added this test, but the exception handling is not well designed yet
def test_lib_retries_10_nones(mock_provider:MockProviderFixture, config:TestConfig):
    mock_provider.provider.poll_test.side_effect = [None] * 10
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
    
    with pytest.raises(InternalError):
        test.run()
    
    assert test.get_state().test_complete == False, "the test should not be completed"

# TODO: hurriedly added this test, but the exception handling is not well designed yet
def test_lib_retries_resets(mock_provider:MockProviderFixture, config:TestConfig):
    mock_provider.provider.poll_test.side_effect = [None] * 9 + [FetchTestDataResponse(has_finished=False, risk=0, attacks=[])] + [None] * 9 + [FetchTestDataResponse(has_finished=True, risk=0, attacks=[])]
    test = Test(config, poll_period_seconds=0)
    test._provider = mock_provider.provider # type: ignore # TODO: fixme
    
    test.run()
    assert test.get_state().test_complete == True, "the test should be completed"