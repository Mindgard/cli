
from dataclasses import dataclass, field
from threading import Condition, Thread
import time
from typing import Any, Callable, Optional, Tuple
from unittest import mock
from unittest.mock import MagicMock, patch

from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, WebPubSubDataType

from mindgard.wrappers import Context, ModelWrapper
from ...src.mindgard import auth
import pytest
from pytest_snapshot.plugin import Snapshot
# from typing import NamedTuple
# from unittest.mock import MagicMock
from ...src.mindgard.constants import API_BASE
from ...src.mindgard.run_functions.llm_model_test import llm_test_output_factory, llm_test_polling, llm_test_submit_factory
from ...src.mindgard.run_poll_display import cli_run
from ...src.mindgard.utils import convert_test_to_cli_response
import requests_mock # type: ignore

# allow us to make assertions and capture test issues in background threads
class PropagatingThread(Thread):
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret

class MockModelWrapper(ModelWrapper):
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

@mock.patch("azure.messaging.webpubsubclient.WebPubSubClient", autospec=True)
def test_json_output(
    mock_webpubsubclient: MagicMock,
    capsys: pytest.CaptureFixture[str], 
    snapshot:Snapshot, 
    requests_mock: requests_mock.Mocker,
) -> None:
    
    with patch.object(WebPubSubClient, "__new__", return_value=mock_webpubsubclient), patch.object(WebPubSubClientCredential, "__init__", return_value=None):
        open_notifier = Condition()
        subscribe_notifier = Condition()
        client_message_notifier = Condition()
        test_finished_notifier = Condition()
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

        def fake_webpubsub_interactions():

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
                    "payload": {"groupId": "group_id"},
                }, "json")
            
            # TODO test_id is the ongoing assertion
            test_context.client_listener(OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "", "messageType": "StartedTest", "payload": {"testId": "test_id"}}))

            # send some prompts
            messages = [
                "world1",
                "world2",
            ]
            expect_messages = [MockModelWrapper.mirror(x) for x in messages]
            for message in messages:
                test_context.client_listener(OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "", "messageType": "Request", "payload": {"prompt": message}}))

            # expect some responses
            with client_message_notifier:
                assert True == False
                while len(test_context.client_sent_messages) != 1 + len(messages):
                    assert client_message_notifier.wait(1) == True

                assert len(test_context.client_sent_messages) == 1 + len(messages)
                for idx, expect_response in enumerate(expect_messages):
                    got = test_context.client_sent_messages[idx]
                    assert got[0] == "orchestrator"
                    assert got[1]["payload"]["response"] == expect_response
                        

            # this allows the test to finish (i.e. simulate the polling completion)
            with test_finished_notifier:
                test_context.test_finished = True
                test_finished_notifier.notify_all()

        # 
        t_wps = PropagatingThread(target=fake_webpubsub_interactions)
        t_wps.start()

        auth.load_access_token = MagicMock(return_value="atoken")

        requests_mock.post(
            f"{API_BASE}/tests/cli_init",
            json={
                "url": "dsfdfsdf",
                "groupId": "group_id",
            },
            status_code=200,
        )

        requests_mock.get(
            f"{API_BASE}/assessments/test_id",
            #TODO: should switch finished after messages are exchanged additional_matcher= 
            additional_matcher=lambda req: test_context.test_finished,
            json={
                "id": "test_id",
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
                "hasFinished": True,
                "risk": 13,
            },
            status_code=200,
        )

        requests_mock.get(
            f"{API_BASE}/assessments/test_id",
            #TODO: should switch finished after messages are exchanged additional_matcher= 
            additional_matcher=lambda req: not test_context.test_finished,
            json={
                "id": "test_id",
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
            },
            status_code=200,
        )

        model_wrapper = MockModelWrapper()

        submit = llm_test_submit_factory(
            target="mymodel",
            parallelism=4,
            system_prompt="my system prompt",
            model_wrapper=model_wrapper
        )
        output = llm_test_output_factory(risk_threshold=50)
        cli_response = cli_run(submit, llm_test_polling, output_func=output, json_out=True)
        res = convert_test_to_cli_response(test=cli_response, risk_threshold=50)

        assert res.code() == 0
        captured = capsys.readouterr()
        stdout = captured.out
        snapshot.assert_match(stdout, 'stdout.json')

        t_wps.join()


@mock.patch("azure.messaging.webpubsubclient.WebPubSubClient", autospec=True)
def test_text_output(
    mock_webpubsubclient: MagicMock,
    capsys: pytest.CaptureFixture[str], 
    snapshot:Snapshot, 
    requests_mock: requests_mock.Mocker,
) -> None:
    
    with patch.object(WebPubSubClient, "__new__", return_value=mock_webpubsubclient), patch.object(WebPubSubClientCredential, "__init__", return_value=None):
        open_notifier = Condition()
        subscribe_notifier = Condition()
        client_message_notifier = Condition()
        test_finished_notifier = Condition()
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

        def fake_webpubsub_interactions():

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
                        "payload": {"groupId": "group_id"},
                    }, "json")
            
            # TODO test_id is the ongoing assertion
            test_context.client_listener(OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "", "messageType": "StartedTest", "payload": {"testId": "test_id"}}))

            # send some prompts
            messages = [
                "world1",
                "world2"
            ]
            expect_messages = [MockModelWrapper.mirror(x) for x in messages]
            for message in messages:
                test_context.client_listener(OnGroupDataMessageArgs(group="group id", data_type=WebPubSubDataType.JSON, data={"correlationId": "", "messageType": "Request", "payload": {"prompt": message}}))

            # expect some responses
            with client_message_notifier:
                while len(test_context.client_sent_messages) != 3:
                    assert client_message_notifier.wait(1) == True
                    assert len(test_context.client_sent_messages) == 3
                    for idx, expect_response in enumerate(expect_messages):
                        got = test_context.client_sent_messages[idx]
                        assert got[0] == "orchestrator"
                        assert got[1]["payload"]["response"] == expect_response

            # this allows the test to finish (i.e. simulate the polling completion)
            with test_finished_notifier:
                test_context.test_finished = True
                test_finished_notifier.notify_all()

        # 
        t_wps = PropagatingThread(target=fake_webpubsub_interactions)
        t_wps.start()

        auth.load_access_token = MagicMock(return_value="atoken")

        requests_mock.post(
            f"{API_BASE}/tests/cli_init",
            json={
                "url": "dsfdfsdf",
                "groupId": "group_id",
            },
            status_code=200,
        )

        requests_mock.get(
            f"{API_BASE}/assessments/test_id",
            #TODO: should switch finished after messages are exchanged additional_matcher= 
            additional_matcher=lambda req: test_context.test_finished,
            json={
                "id": "test_id",
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
                "hasFinished": True,
                "risk": 13,
            },
            status_code=200,
        )

        requests_mock.get(
            f"{API_BASE}/assessments/test_id",
            #TODO: should switch finished after messages are exchanged additional_matcher= 
            additional_matcher=lambda req: not test_context.test_finished,
            json={
                "id": "test_id",
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
            },
            status_code=200,
        )

        model_wrapper = MockModelWrapper()

        submit = llm_test_submit_factory(
            target="mymodel",
            parallelism=4,
            system_prompt="my system prompt",
            model_wrapper=model_wrapper
        )
        output = llm_test_output_factory(risk_threshold=50)
        cli_response = cli_run(submit, llm_test_polling, output_func=output, json_out=False)
        res = convert_test_to_cli_response(test=cli_response, risk_threshold=50)

        assert res.code() == 0
        captured = capsys.readouterr()
        stdout = captured.out
        snapshot.assert_match(stdout, 'stdout.txt')

        t_wps.join()