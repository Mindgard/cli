"""
Status: Pre-Alpha -- implementation incomplete and interfaces are likely to change

Provides headless execution of mindgard tests.
"""

import contextlib
import copy
from dataclasses import dataclass, field
import logging
from threading import Condition
import time
from typing import Any, Callable, Dict, Literal, Optional, Protocol, Tuple, List
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, CallbackType, WebPubSubDataType
import requests
from mindgard.constants import DEFAULT_RISK_THRESHOLD
from mindgard.mindgard_api import AttackResponse, FetchTestDataResponse, MindgardApi

from mindgard.version import VERSION

# surpress distracting warning messages from azure webpubsubclient; aims to be as precise as possible
# https://github.com/Azure/azure-sdk-for-python/issues/37390
logging.getLogger('azure.messaging.webpubsubclient._client').addFilter(
    lambda record: not(record.getMessage() == "The client is stopping state. Stop recovery." and record.levelno == logging.WARNING)
)

class RequestHandler(Protocol):
    """
    Protocol for converting a Request paylod to a Response payload
    """
    def __call__(self, payload: Any) -> Any: ...

class _Wrapper(Protocol):
    """
    Protocol for supplied model wrappers
    """

    def to_handler(self) -> RequestHandler: ...

@dataclass
class ModelConfig:
    wrapper: _Wrapper
    def to_orchestrator_init_params(self) -> Dict[str, Any]:
        return {}
    
@dataclass
class ImageModelConfig(ModelConfig):
    dataset: str
    labels: list[str]
    model_type: str = "image"

    def to_orchestrator_init_params(self) -> Dict[str, Any]:
        return {
            "modelType": self.model_type,
            "dataset": self.dataset,
            "labels": self.labels,
        }

@dataclass
class LLMModelConfig(ModelConfig):
    system_prompt: str
    model_type: str = "llm"

    def to_orchestrator_init_params(self) -> Dict[str, Any]:
        return {
            "modelType": self.model_type,
            "system_prompt": self.system_prompt,
        }

@dataclass
class TestConfig:
    api_base: str
    api_access_token: str
    target: str
    attack_source: str
    parallelism: int
    model: ModelConfig
    attack_pack: str = "sandbox"
    additional_headers: Optional[Dict[str, str]] = None
    risk_threshold: int = DEFAULT_RISK_THRESHOLD
    def to_orchestrator_init_params(self) -> Dict[str, Any]:
        """
        Get parameters for the init test request to orchestrator
        """
        return {**{
            "target": self.target,
            "attackPack": self.attack_pack,
            "parallelism": self.parallelism,
            "attackSource": self.attack_source
        }, **self.model.to_orchestrator_init_params()}

    def handler(self) -> RequestHandler:
        return self.model.wrapper.to_handler()

@dataclass
class AttackState():
    id: str
    name: str
    state: Literal["queued", "running", "completed"]
    errored: Optional[bool] = None
    passed: Optional[bool] = None
    risk: Optional[int] = None

@dataclass
class TestState():
    submitting: bool = False
    submitted: bool = False
    started: bool = False
    test_complete: bool = False
    attacks: List[AttackState] = field(default_factory=list[AttackState])
    model_exceptions: List[Exception] = field(default_factory=list[Exception])
    test_id: Optional[str] = None

    def clone(self):
        return TestState(
            submitting=self.submitting,
            submitted=self.submitted,
            started=self.started,
            test_complete=self.test_complete,
            attacks=copy.deepcopy(self.attacks),
            model_exceptions=copy.deepcopy(self.model_exceptions),
            test_id=self.test_id
        )
class TestImplementationProvider():

    def __init__(self, mindgard_api:Optional[MindgardApi] = None):
        self._mindgard_api = mindgard_api or MindgardApi()

    def init_test(self, config:TestConfig) -> Tuple[str, str]:
        """
        Init a test in with API and return the url and group_id
        """
        url = f"{config.api_base}/tests/cli_init"

        response = requests.post(
            url=url, 
            headers={
                "Authorization": f"Bearer {config.api_access_token}",
                "User-Agent": f"mindgard-cli/{VERSION}",
                "X-User-Agent": f"mindgard-cli/{VERSION}",
                **(config.additional_headers or {})
            },
            json=config.to_orchestrator_init_params()
        )
        response.raise_for_status()

        url = response.json().get("url", None)
        group_id = response.json().get("groupId", None)
        if not url or not group_id:
            raise ValueError("Invalid response from orchestrator, missing websocket credentials.")

        return url, group_id
    
    def create_client(self, connection_url:str) -> WebPubSubClient:
        credentials = WebPubSubClientCredential(client_access_url_provider=connection_url)
        return WebPubSubClient(credential=credentials)

    def connect_websocket(self, client:WebPubSubClient) -> None:
        client.open()

    def register_handler(self, handler:RequestHandler, client:WebPubSubClient, group_id:str) -> None:
        def callback(msg:OnGroupDataMessageArgs) -> None:
            if msg.data["messageType"] != "Request":
                return

            payload = handler(payload=msg.data["payload"])
            
            client.send_to_group(
                "orchestrator",
                {
                    "correlationId": msg.data["correlationId"],
                    "messageType": "Response",
                    "status": "ok",
                    "payload": payload
                },
                data_type=WebPubSubDataType.JSON
            )
            
        client.subscribe(CallbackType.GROUP_MESSAGE, callback)

    def start_test(self, client:WebPubSubClient, group_id:str) -> str:
        logging.info(f"start_test: opening connection and starting test")
        started_condition = Condition()
        test_ids: list[str] = []
        def handler(msg:OnGroupDataMessageArgs) -> None:
            logging.debug(f"received message {msg.data}")
            if msg.data["messageType"] == "StartedTest":
                with started_condition:
                    test_ids.append(msg.data["payload"]["testId"])
                    started_condition.notify_all()

        client.subscribe(CallbackType.GROUP_MESSAGE, handler)
        payload:Dict[str, Any] = {
            "correlationId": "",
            "messageType": "StartTest",
            "payload": {"groupId": group_id},
        }
        client.send_to_group(group_name="orchestrator", content=payload, data_type=WebPubSubDataType.JSON)
        
        logging.info("start_test: waiting for test_id")
        with started_condition:
            started_condition.wait_for(lambda: len(test_ids) > 0)
            test_id = test_ids[0]
            logging.info(f"start_test: received test_id {test_id}")
            return test_id

    def poll_test(self, config:TestConfig, test_id:str) -> Optional[FetchTestDataResponse]:
        return self._mindgard_api.fetch_test_data(
            api_base=config.api_base,
            access_token=config.api_access_token,
            additional_headers=config.additional_headers,
            test_id=test_id
        )

    def close(self, client:Optional[WebPubSubClient]) -> None:
        if client:
            client.close()

def _attack_response_to_attack_state(attack_data:AttackResponse, risk_threshold: int) -> AttackState:
    return AttackState(
        id=attack_data.id,
        name=attack_data.name,
        state=attack_data.state,
        errored=attack_data.errored,
        passed=None if attack_data.risk is None else (attack_data.risk < risk_threshold),
        risk=None if attack_data.errored else attack_data.risk
    )

class Test():
    def __init__(self, config:TestConfig, poll_period_seconds:float = 5):
        self._config = config
        self._state = TestState() # TOOD: coverage
        self._provider = TestImplementationProvider() # TOOD: coverage
        self._notifier = Condition()
        self._poll_period_seconds = poll_period_seconds

    # for clients to observe state[changes]
    def get_state(self) -> TestState:
        with self._notifier:
            return self._state.clone()
        
    @contextlib.contextmanager
    def state_then_wait_if(self, predicate:Callable[[TestState], bool]):
        with self._notifier:
            yield self.get_state()
            if predicate(self._state):
                self._notifier.wait()

    # TODO: coverage
    @contextlib.contextmanager
    def state_wait(self):
        with self._notifier:
            self._notifier.wait()
            yield self._state

    # TODO: coverage
    @contextlib.contextmanager
    def state_wait_for(self, predicate:Callable[[TestState], bool]):
        with self._notifier:
            self._notifier.wait_for(lambda: predicate(self._state))
            yield self._state
    
    def _set_started(self) -> None:
        with self._notifier:
            self._state.started = True
            self._notifier.notify_all()

    def _set_submitting_test(self) -> None:
        with self._notifier:
            self._state.submitting = True
            self._notifier.notify_all()

    def _set_attacking(self, test_id:str, attacks:List[AttackState]) -> None:
        with self._notifier:
            self._state.submitted = True
            self._state.test_id = test_id
            self._state.attacks = attacks
            self._state.started = True
            self._notifier.notify_all()

    def _set_test_complete(self, test_id:str, attacks:List[AttackState]) -> None:
        with self._notifier:
            self._state.test_id = test_id
            self._state.attacks = attacks
            self._state.test_complete = True
            self._notifier.notify_all()

    def _add_exception(self, exception:Exception) -> None:
        with self._notifier:
            self._state.model_exceptions.append(exception)
            self._notifier.notify_all()

    # run the test
    def run(self) -> None:
        self._set_started()
        p = self._provider
        wps_client = None
        test_id = None
        try:
            self._set_submitting_test()
            wps_url, group_id = p.init_test(self._config)
            wps_client = p.create_client(wps_url)
            p.connect_websocket(wps_client)
            handler = self._config.handler()
            p.register_handler(handler, wps_client, group_id)
            test_id = p.start_test(wps_client, group_id)

            finished = False
            while not finished:
                test_data = p.poll_test(
                    config=self._config,
                    test_id=test_id
                )
                if test_data is not None:
                    finished = test_data.has_finished
                    attacks = [_attack_response_to_attack_state(attack_data, self._config.risk_threshold) for attack_data in test_data.attacks]
                    if finished:
                        self._set_test_complete(test_id, attacks)
                    else:
                        self._set_attacking(test_id, attacks)
                if not finished:
                    time.sleep(self._poll_period_seconds)
        finally:
            p.close(wps_client)