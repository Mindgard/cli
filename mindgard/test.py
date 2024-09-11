"""
Status: Pre-Alpha -- implementation incomplete and interfaces are likely to change

Provides headless execution of mindgard tests.
"""

from dataclasses import dataclass, field
import logging
from threading import Condition
import time
from typing import Any, Dict, Literal, Optional, Protocol, Tuple, List
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, CallbackType, WebPubSubDataType
import requests
from mindgard.mindgard_api import MindgardApi
from mindgard.wrappers.image import ImageModelWrapper

from mindgard.version import VERSION
from mindgard.wrappers.llm import LLMModelWrapper

class RequestHandler(Protocol):
    """
    Protocol for converting a Request paylod to a Response payload
    """
    def __call__(self, payload: Any) -> Any: ...

@dataclass
class ModelConfig:
    def to_orchestrator_init_params(self) -> Dict[str, Any]:
        return {}


@dataclass
class ImageModelConfig(ModelConfig):
    wrapper: ImageModelWrapper
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
    wrapper: LLMModelWrapper
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

    def handler(self) -> Any:
        return self.model.wrapper.to_handler() # type: ignore # TODO not sure on type

@dataclass
class AttackState():
    id: str
    name: str
    state: Literal["queued", "running", "completed"]
    errored: Optional[bool]
    passed: Optional[bool]
    risk: Optional[int]
    

@dataclass
class TestState():
    notifier: Condition = field(default_factory=Condition)
    
    submitting: bool = False
    submitted: bool = False
    started: bool = False
    test_complete: bool = False
    attacks: List[AttackState] = field(default_factory=list[AttackState])
    model_exceptions: List[Exception] = field(default_factory=list[Exception])
    test_id: Optional[str] = None

    def set_started(self) -> None:
        with self.notifier:
            self.started = True
            self.notifier.notify_all()

    def set_submitting_test(self) -> None:
        with self.notifier:
            self.submitting = True
            self.notifier.notify_all()

    def set_attacking(self, test_id:str, attacks:List[AttackState]) -> None:
        with self.notifier:
            self.submitted = True
            self.test_id = test_id
            self.attacks = attacks
            self.started = True
            self.notifier.notify_all()

    def set_test_complete(self, test_id:str, attacks:List[AttackState]) -> None:
        with self.notifier:
            self.test_id = test_id
            self.attacks = attacks
            self.test_complete = True
            self.notifier.notify_all()

    def add_exception(self, exception:Exception) -> None:
        with self.notifier:
            self.model_exceptions.append(exception)
            self.notifier.notify_all()

def api_response_to_attack_state(attack:Dict[str, Any]) -> AttackState:
    if attack["state"] == 0:
        state = "queued"
    elif attack["state"] == 1:
        state = "running"
    else:
        state = "completed"

    errored = (state == "completed" and attack["state"] == -1) or None
    risk = attack.get("risk") if attack["state"] == 2 else None
    return AttackState(
        id=attack["id"],
        name=attack["attack"],
        state=state,
        errored=errored,
        passed=attack.get("passed", None),
        risk=risk
    )

class TestImplementationProvider():

    def __init__(self, state:Optional[TestState] = None):
        self._state = state or TestState()
        self._mindgard_api = MindgardApi()

    def init_test(self, config:TestConfig) -> Tuple[str, str]:
        """
        Init a test in with API and return the url and group_id
        """
        self._state.set_submitting_test()
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
        payload = {
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

    def poll_test(self, config:TestConfig, test_id:str, period_seconds:int = 5) -> None:
        finished = False
        while not finished:
            test_data = self._mindgard_api.fetch_test_data(
                api_base=config.api_base,
                access_token=config.api_access_token,
                additional_headers=config.additional_headers,
                test_id=test_id
            )
            if test_data is not None:
                finished = test_data.has_finished
                attacks = [AttackState(
                    id=attack_data.id,
                    name=attack_data.name,
                    state=attack_data.state,
                    errored=attack_data.errored,
                    passed=None,
                    risk=attack_data.risk
                ) for attack_data in test_data.attacks]

                if finished:
                    self._state.set_test_complete(test_id, attacks)
                else:
                    self._state.set_attacking(test_id, attacks)
   
            time.sleep(period_seconds)

    def close(self, client:Optional[WebPubSubClient]) -> None:
        if client:
            client.close()
            
class Test:
    def __init__(self, config:TestConfig, provider:TestImplementationProvider = TestImplementationProvider()):
        self._config = config
        self._provider = provider

    def run(self) -> None:
        p = self._provider
        wps_client = None
        try:
            wps_url, group_id = p.init_test(self._config)
            logging.info("Creating webpubsub client")
            wps_client = p.create_client(wps_url)
            logging.info("Connecting to webpubsub client")
            p.connect_websocket(wps_client)
            handler = self._config.handler()
            p.register_handler(handler, wps_client, group_id)
            logging.info("Submitting test")
            test_id = p.start_test(wps_client, group_id)
            logging.info("Polling test...")
            p.poll_test(self._config, test_id)
            logging.info("...Test complete!")
        finally:
            logging.info("Closing webpubsub client")
            p.close(wps_client)