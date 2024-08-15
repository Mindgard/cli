

from dataclasses import dataclass
import logging
from threading import Condition
import time
from typing import Tuple
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs, CallbackType, WebPubSubDataType
import requests

from mindgard.version import VERSION
from mindgard.wrappers.llm import LLMModelWrapper

@dataclass
class TestConfig:
    api_base: str
    api_access_token: str

    wrapper: LLMModelWrapper
    target: str

    target: str
    model_type: str
    system_prompt: str
    attack_source: str
    parallelism: int

    attack_pack: str = "sandbox"

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
            },
            json={
                "target": config.target,
                "modelType": config.model_type,
                "system_prompt": config.system_prompt,
                "attackPack": config.attack_pack,
                "parallelism": config.parallelism,
                "attackSource": config.attack_source
            }
        )
        response.raise_for_status()

        url = response.json().get("url", None)
        group_id = response.json().get("groupId", None)
        if not url or not group_id:
            raise ValueError("Invalid response from orchestrator, missing websocket credentials.")

        return url, group_id
    
    def connect_websocket(self, connection_url:str) -> WebPubSubClient:
        credentials = WebPubSubClientCredential(client_access_url_provider=connection_url)
        client =  WebPubSubClient(credential=credentials)
        client.open()
        return client
        
    def register_wrapper(self, config:TestConfig, client:WebPubSubClient, group_id:str) -> None:
        def callback(msg:OnGroupDataMessageArgs) -> None:
            if msg.data["messageType"] != "Request":
                return
            
            res = config.wrapper.__call__(content=msg.data["payload"]["prompt"])

            client.send_to_group(
                "orchestrator",
                {
                    "correlationId": msg.data["correlationId"],
                    "messageType": "Response",
                    "status": "ok",
                    "payload": {
                        "response": res,
                        "error": None
                    }
                },
                data_type=WebPubSubDataType.JSON
            )
            
        client.subscribe(CallbackType.GROUP_MESSAGE, callback)

    def start_test(self, client:WebPubSubClient, group_id:str):
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

    def poll_test(self, config:TestConfig, test_id:str, period_seconds:int = 5):
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
            except requests.JSONDecodeError:
                # TODO logging
                pass
            except KeyError:
                # TODO logging
                pass
                
            time.sleep(period_seconds)
            


class Test:
    def __init__(self, config:TestConfig, provider:TestImplementationProvider = TestImplementationProvider()):
        self._config = config
        self._provider = provider

    def run(self): 
        p = self._provider
        wps_url, group_id = p.init_test(self._config)
        wps_client = p.connect_websocket(wps_url)
        p.register_wrapper(self._config, wps_client, group_id)
        test_id = p.start_test(wps_client, group_id)
        p.poll_test(self._config, test_id)