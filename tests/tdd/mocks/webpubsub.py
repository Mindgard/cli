from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

from typing import Callable

import time
from unittest.mock import Mock

from typing import Dict, Any

credentials = Mock(spec=WebPubSubClientCredential)
ws_client = Mock(spec=WebPubSubClient)
ws_client.send_to_group.return_value = None


def wait_and_call_factory(payload: Dict[str, Any]):  # type: ignore
    def wait_and_call(
        _: str, callback: Callable[[OnGroupDataMessageArgs], None]
    ) -> None:
        time.sleep(0.5)
        message = OnGroupDataMessageArgs(group="orchestrator", data_type="json", data=payload)  # type: ignore
        callback(message)

    return wait_and_call
