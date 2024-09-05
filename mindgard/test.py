"""
Status: Pre-Alpha -- implementation incomplete and interfaces are likely to change

Provides headless execution of mindgard tests.
"""

from dataclasses import dataclass
import logging
from threading import Condition
import time
from typing import Any, Dict, Optional, Protocol, Tuple
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, CallbackType, WebPubSubDataType
import requests
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


class TestImplementationProvider():

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
        logging.error(f"Starting test {group_id}")
        started_condition = Condition()
        test_ids: list[str] = []
        def handler(msg:OnGroupDataMessageArgs) -> None:
            logging.error(f"received message {msg.data}")
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
        
        logging.error("waiting for test to start")
        with started_condition:
            started_condition.wait_for(lambda: len(test_ids) > 0)
            return test_ids[0]

    def poll_test(self, config:TestConfig, test_id:str, period_seconds:int = 5) -> None:
        finished = False
        while not finished:
            response = requests.get(
                url=f"{config.api_base}/assessments/{test_id}",
                headers={
                    "Authorization": f"Bearer {config.api_access_token}",
                }
            )
            try:
                if response.status_code == 200:
                    test = response.json()
                    finished = test["hasFinished"]
                    logging.info(f"Test {test_id} has finished! {test['hasFinished']} {test['isCompleted']}")
            except requests.JSONDecodeError as jde:
                logging.error(f"Error decoding response: {jde}")
                pass
            except KeyError as ke:
                logging.error(f"KeyError response: {ke}")
                pass
                
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