import ctypes
from dataclasses import dataclass, field
import json
import os
import platform
from threading import Condition, Thread
import time
from typing import Any, Callable, Optional, Tuple
from unittest import mock
from unittest.mock import MagicMock, patch

from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, WebPubSubDataType

from mindgard.external_model_handlers.llm_model import llm_message_handler
from mindgard.orchestrator import OrchestratorSetupRequest
from mindgard.run_functions.external_models import model_test_output_factory, model_test_polling, model_test_submit_factory
from mindgard.wrappers.llm import Context, LLMModelWrapper
from mindgard import auth
import pytest
from pytest_snapshot.plugin import Snapshot
# from typing import NamedTuple
# from unittest.mock import MagicMock
from mindgard.constants import API_BASE
from mindgard.run_poll_display import cli_run
from mindgard.utils import convert_test_to_cli_response
import requests_mock # type: ignore

# allow us to make assertions and capture test issues in background threads
class PropagatingThread(Thread):
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs) # type: ignore
        except BaseException as e:
            self.exc = e

    def join(self, timeout:Optional[float]=None) -> Any:
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret # type: ignore

class MockModelWrapper(LLMModelWrapper):
    @classmethod
    def mirror(cls, input:str) -> str:
        time.sleep(0.1)
        return "hello " + input
    
    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        return self.mirror(content) # mirror the input for later assertions

@dataclass
class _TestContext():
    have_called_open: bool = False
    have_set_listener: bool = False
    client_listener: Callable[[OnGroupDataMessageArgs], None] = lambda x: None
    client_sent_messages: list[Tuple[str, dict[Any,Any], str]] = field(default_factory=list)
    test_finished: bool = False
    cli_completed: bool = False

fixture_test_id = "my-test-id"
fixture_group_id = "my-group-id"
fixture_cli_init_response = {
    "url": "dsfdfsdf",
    "groupId": fixture_group_id,
}
fixture_test_not_finished_response = {
    "id": fixture_test_id,
    "mindgardModelName": "mistral",
    "source": "mindgard",
    "createdAt": "2021-09-01T00:00:00.000Z",
    "attacks": [
        {
            "id": "example_id_1",
            "submitted_at": "2021-09-01T00:00:00.000Z",
            "submitted_at_unix": 1630454400.0,
            "run_at": "2021-09-01T00:00:00.000Z",
            "run_at_unix": 1630454400.0,
            "state": 2,
            "state_message": "Running",
            "runtime": 10.5,
            "model": "mymodel",
            "dataset": "mydataset",
            "attack": "myattack",
            "risk": 12,
            "stacktrace": None,        
        },
        {
            "id": "example_id_2",
            "submitted_at": "2021-09-01T00:00:00.000Z",
            "submitted_at_unix": 1630454400.0,
            "run_at": "2021-09-01T00:00:00.000Z",
            "run_at_unix": 1630454400.0,
            "state": 2,
            "state_message": "Running",
            "runtime": 10.5,
            "model": "mymodel",
            "dataset": "mydataset",
            "attack": "myattack",
            "risk": 12,
            "stacktrace": None,        
        }
    ],
    "isCompleted": True,
    "hasFinished": False,
    "risk": 13,
}
fixture_test_finished_response = fixture_test_not_finished_response.copy()
fixture_test_finished_response["hasFinished"] = True

def _run_llm_test(json_out:bool = True, model_type:str = 'llm') -> None:
    auth.load_access_token = MagicMock(return_value="atoken")
    model_wrapper = MockModelWrapper()

    request = OrchestratorSetupRequest(
        target="mymodel",
        parallelism=4,
        system_prompt="my system prompt",
        dataset=None,
        modelType=model_type,
        attackSource="user"
    )
    submit = model_test_submit_factory(
        request=request,
        model_wrapper=model_wrapper,
        message_handler=llm_message_handler
    )
    output = model_test_output_factory(risk_threshold=50)
    cli_response = cli_run(submit, model_test_polling, output_func=output, json_out=json_out)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=50)

    assert res.code() == 0

def _test_inner(run_inner: Callable[[],None], requests_mock: requests_mock.Mocker) -> Any:
    """
    Provides a mock test execution, simulating:
     * webpubsub interactions
     * message exchange (prompt -> response)
     * test completion (!hasFinished -> hasFinished)

    Args:
        run_inner: The inner function that contains the test logic.
        requests_mock: The mock object for making HTTP requests.
    """
    with mock.patch("azure.messaging.webpubsubclient.WebPubSubClient") as mock_webpubsubclient:
        with patch.object(WebPubSubClient, "__new__", return_value=mock_webpubsubclient), patch.object(WebPubSubClientCredential, "__new__", return_value=None):
            open_notifier = Condition()
            subscribe_notifier = Condition()
            client_message_notifier = Condition()
            test_finished_notifier = Condition()
            cli_finished = Condition()
            test_context = _TestContext()

            def subscribe(event:str, listener:Callable[[OnGroupDataMessageArgs], None]) -> None:
                assert event == "group-message"
                with subscribe_notifier:
                    test_context.client_listener = listener
                    test_context.have_set_listener = True
                    subscribe_notifier.notify_all()

            def send_to_group(group_name:str, content:dict[Any,Any], data_type:str) -> None:
                with client_message_notifier:
                    test_context.client_sent_messages.append((group_name, content, data_type))
                    client_message_notifier.notify_all()

            def open() -> None:
                with open_notifier:
                    test_context.have_called_open = True
                    open_notifier.notify_all()

            mock_webpubsubclient.open = MagicMock(side_effect=open)
            mock_webpubsubclient.subscribe = MagicMock(side_effect=subscribe)
            mock_webpubsubclient.send_to_group = MagicMock(side_effect=send_to_group)

            submit_test_mock = requests_mock.post(
                f"{API_BASE}/tests/cli_init",
                json=fixture_cli_init_response,
                status_code=200,
            )

            requests_mock.get(
                f"{API_BASE}/assessments/{fixture_test_id}",
                additional_matcher=lambda req: test_context.test_finished,
                json=fixture_test_finished_response,
                status_code=200,
            )

            requests_mock.get(
                f"{API_BASE}/assessments/{fixture_test_id}",
                #TODO: should switch finished after messages are exchanged additional_matcher= 
                additional_matcher=lambda req: not test_context.test_finished,
                json=fixture_test_not_finished_response,
                status_code=200,
            )

            def run_test() -> None:
                try:
                    run_inner()
                finally: # if the inner assertions fail, speed up the test completion
                    with cli_finished:
                        test_context.cli_completed = True
                        cli_finished.notify_all()

            t_run_test = PropagatingThread(target=run_test) # run the actual test target
            t_run_test.start()
            try:
                # wait for open call
                with open_notifier:
                    if not test_context.have_called_open:
                        assert open_notifier.wait(1) == True

                # wait for subscribe call
                with subscribe_notifier:
                    if not test_context.have_set_listener:
                        assert subscribe_notifier.wait(1) == True

                # check we received the start test message
                with client_message_notifier:
                    if len(test_context.client_sent_messages) == 0:
                        assert client_message_notifier.wait(1) == True
                    
                    assert len(test_context.client_sent_messages) == 1
                    assert test_context.client_sent_messages[0] == ("orchestrator", {
                        "correlationId": "",
                        "messageType": "StartTest",
                        "payload": {"groupId": fixture_group_id},
                    }, "json")
                
                # TODO test_id is the ongoing assertion
                test_context.client_listener(OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "", "messageType": "StartedTest", "payload": {"testId": fixture_test_id}}))

                # send some prompts
                messages = [
                    ("correl_id1", "world1"),
                    ("correl_id2", "world2"),
                ]
                expect_messages = [(x[0], MockModelWrapper.mirror(x[1])) for x in messages]
                for message in messages:
                    test_context.client_listener(OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": message[0], "messageType": "Request", "payload": {"prompt": message[1]}}))

                # expect some responses
                with client_message_notifier:
                    while len(test_context.client_sent_messages) != 1 + len(messages):
                        assert client_message_notifier.wait(1) == True

                    assert len(test_context.client_sent_messages) == 1 + len(messages)
                    for idx, expect_response in enumerate(expect_messages):
                        got = test_context.client_sent_messages[idx + 1]
                        assert got[0] == "orchestrator"
                        assert got[1]["correlationId"] == expect_response[0]
                        assert got[1]["payload"]["response"] == expect_response[1]
                            

                # this allows the test to finish (i.e. simulate the polling completion)
                with test_finished_notifier:
                    test_context.test_finished = True
                    test_finished_notifier.notify_all()

            finally:
                with cli_finished:
                    if test_context.cli_completed == False:
                        # wait for 20 seconds for the test to complete, then inject an exception to force it to exit
                        if cli_finished.wait(6) == False:
                            thread_ident = t_run_test.ident
                            assert thread_ident is not None
                            class TestTimeoutException(Exception):
                                pass
                            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_ident), ctypes.py_object(TestTimeoutException))
                t_run_test.join()
                assert submit_test_mock.call_count == 1
                assert submit_test_mock.last_request is not None
                return submit_test_mock.last_request.json()

def test_empty_mindgard_extra_config(requests_mock: requests_mock.Mocker):
    def run_test():
        with mock.patch.dict('os.environ'):
            if "MINDGARD_EXTRA_CONFIG" in os.environ:
                del os.environ["MINDGARD_EXTRA_CONFIG"]
            _run_llm_test()

    submitted_test = _test_inner(run_test, requests_mock)
    assert "extraConfig" not in submitted_test

def test_mindgard_extra_config(requests_mock: requests_mock.Mocker):
    config = {
        "hello": "world",
    }

    def run_test():
        with mock.patch.dict(os.environ, {"MINDGARD_EXTRA_CONFIG": json.dumps(config)}):
            _run_llm_test()

    submitted_test = _test_inner(run_test, requests_mock)
    assert submitted_test is not None
    assert submitted_test.get("extraConfig") == config

def test_image_test_model_type_llm(requests_mock: requests_mock.Mocker) -> None:
    def run_test() -> None:
        _run_llm_test(json_out=False, model_type="llm")
    
    submitted_test =  _test_inner(run_test, requests_mock)
    assert submitted_test.get("modelType") == "llm"
    
def test_image_test_model_type_empty(requests_mock: requests_mock.Mocker) -> None:
    def run_test() -> None:
        _run_llm_test(json_out=False)
    
    submitted_test =  _test_inner(run_test, requests_mock)
    assert submitted_test.get("modelType") == "llm"
    
def test_image_test_model_type_image(requests_mock: requests_mock.Mocker) -> None:
    def run_test() -> None:
        _run_llm_test(json_out=False, model_type="image")
    
    submitted_test =  _test_inner(run_test, requests_mock)
    assert submitted_test.get("modelType") == "image"

def test_json_output(
    capsys: pytest.CaptureFixture[str], 
    snapshot:Snapshot, 
    requests_mock: requests_mock.Mocker,
) -> None:
    def run_test() -> None:
        _run_llm_test()
        captured = capsys.readouterr()
        stdout = captured.out
        snapshot.assert_match(stdout, 'stdout.json')

    _test_inner(run_test, requests_mock)

def test_text_output(
    capsys: pytest.CaptureFixture[str], 
    snapshot:Snapshot, 
    requests_mock: requests_mock.Mocker,
) -> None:
    def run_test() -> None:
        _run_llm_test(json_out=False)
        
        captured = capsys.readouterr()
        stdout = captured.out
        if platform.system() == "Windows":
            # TODO: this is a basic check as Rich renders differently on windows
            assert f"Results - https://sandbox.mindgard.ai/r/test/{fixture_test_id}" in stdout
            assert "Attack myattack done success" in stdout
        else:
            snapshot.assert_match(stdout, 'stdout.txt')    

    _test_inner(run_test, requests_mock)
