import logging
from dataclasses import dataclass
from typing import Literal, Optional, Union

from pydantic import BaseModel

import requests

from mindgard.exceptions import MGException


@dataclass
class StartReconRequest:
    target_name: str
    access_token: str


@dataclass
class StartReconResponse:
    id: str


AllowedEventTypes = Literal['prompt_request', 'complete']


class GetEventRequest(BaseModel):
    source_id: str
    event_type: list[AllowedEventTypes]
    access_token: str


class GetReconnRequest(BaseModel):
    recon_id: str
    access_token: str


class ReconnResult(BaseModel):
    guardrail_detected: bool
    detected_guardrails: list[str] = []


class GetReconnResponse(BaseModel):
    id: str
    state: str
    result: Optional[ReconnResult] = None
    reason: Optional[str] = None
    recommendation: Optional[str] = None
    target_name: str


class PromptRequest(BaseModel):
    prompt: str
    language: str


class PromptResult(BaseModel):
    content: Optional[str] = None
    duration_ms: Optional[float] = None
    prompt_request: PromptRequest
    error_message: Optional[str] = None
    error_code: Optional[int] = None


class ReceivedEvent(BaseModel):
    event_id: str
    event_type: str
    source_id: str
    prompt_request: Optional[list[PromptRequest]] = None


RESULT_EVENT_TYPE = Literal['prompt_result']


class PushPromptRequest(BaseModel):
    source_id: str
    event_type: RESULT_EVENT_TYPE
    prompt_result: list[PromptResult]
    access_token: str

    def to_api_request(self) -> dict:
        return {
            "source_id": self.source_id,
            "event_type": self.event_type,
            "prompt_result": [r.model_dump() for r in self.prompt_result]
        }


class PushPromptResultsResponse(BaseModel):
    event_id: str


class GuardrailServiceException(MGException):
    status_code: int
    message: str

    def __init__(self, message: str, status_code: int) -> None:
        self.status_code = status_code
        self.message = message


class GuardrailService:
    def __init__(self, reconn_url: str, get_events_url: str, push_events_url: str):
        self.reconn_url = reconn_url
        self.get_events_url = get_events_url
        self.push_events_url = push_events_url

    def start_recon(self, request: StartReconRequest) -> StartReconResponse:
        response = requests.post(self.reconn_url, json={"target_name": request.target_name},
                                 headers={"Authorization": f"Bearer {request.access_token}"})

        if response.status_code != 201:
            logging.debug(f"Failed to start recon: {response.json()} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)
        recon_id = response.json().get("recon_id")
        return StartReconResponse(recon_id)

    def get_recon_event(self, request: GetEventRequest) -> Union[ReceivedEvent, None]:
        request_to_send = {
            "source_id": request.source_id,
            "event_type": request.event_type
        }

        response = requests.post(self.get_events_url, json=request_to_send,
                                 headers={"Authorization": f"Bearer {request.access_token}"})

        if response.status_code == 404:
            logging.debug(f"No event found for source_id={request.source_id}: {response.text}")
            return None

        if response.status_code != 200:
            logging.debug(f"Failed to get recon events: {response.text} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)

        return ReceivedEvent.model_validate(response.json())

    def push_prompt_results(self, request: PushPromptRequest) -> PushPromptResultsResponse:

        response = requests.post(self.push_events_url, json=request.to_api_request(),
                                 headers={"Authorization": f"Bearer {request.access_token}"})
        if response.status_code != 201:
            logging.debug(f"Failed to prompt results: {response.json()} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)
        event_id = response.json().get("event_id")
        return PushPromptResultsResponse.model_validate({
            "event_id": event_id
        })

    def get_recon_result(self, request: GetReconnRequest) -> Union[GetReconnResponse, None]:
        response = requests.get(f"{self.reconn_url}",
                                params={"recon_id": request.recon_id},
                                headers={"Authorization": f"Bearer {request.access_token}"}
                                )

        if response.status_code == 404:
            logging.debug(f"No reconn found for source_id={request.recon_id}: {response.text}")
            return None

        if response.status_code != 200:
            logging.debug(f"Failed to get recon result: {response.text} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)

        return GetReconnResponse.model_validate(response.json())
