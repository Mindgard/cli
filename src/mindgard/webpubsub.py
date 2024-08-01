# Types
from pydantic import BaseModel, model_validator
from typing import Dict, Any, Optional

# Networking
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

# Type aliases
from .types import type_wps_message_type


# Data Models
class WebPubSubMessage(BaseModel):
    messageType: type_wps_message_type
    payload: Dict[str, Any]
    correlationId: Optional[str] = None

    @model_validator(mode="after")  # type: ignore
    def check_StartTest_payload(self):
        if self.messageType == "StartTest":
            if "groupId" not in self.payload:
                raise ValueError("StartTest requires groupId in payload!")

        return self

    @model_validator(mode="after")  # type: ignore
    def check_StartedTest_payload(self):
        if self.messageType == "StartedTest":
            if "testId" not in self.payload:
                raise ValueError("StartedTest requires testId in payload!")

        return self

    @model_validator(mode="after")  # type: ignore
    def check_Request_payload(self):
        if self.messageType == "Request":
            if self.correlationId is None:
                raise ValueError("Request requires correlationId to be valid!")

        return self


def wps_network_message_to_mg_message(
    message: OnGroupDataMessageArgs,
) -> WebPubSubMessage:
    return WebPubSubMessage(**dict(message.data))
