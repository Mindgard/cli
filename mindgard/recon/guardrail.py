import logging
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel

import requests


@dataclass
class StartReconRequest:
    target_name: str
    access_token: str


@dataclass
class StartReconResponse:
    id: str


AllowedEventTypes = Literal['prompt_request', 'complete']


class GetEventRequest(BaseModel):
    reconn_id: str
    types: list[AllowedEventTypes]
    access_token: str


class PromptRequest(BaseModel):
    prompt: str
    sequence: int
    language: str
    is_malicious: bool


class PromptResult(BaseModel):
    content: str
    duration_ms: float
    prompt_request: PromptRequest


class ReceivedEvent(BaseModel):
    event_id: str
    event_type: str
    reconn_id: str
    prompt_request: Optional[list[PromptRequest]] = None


class PushPromptRequest(BaseModel):
    reconn_id: str
    event_type: Literal['prompt_result']
    prompt_response: list[PromptResult]
    access_token: str


class PushPromptResultsResponse(BaseModel):
    event_id: str
    message: str

class GuardrailServiceException(Exception):
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
        response = requests.post(self.reconn_url,
                                 json={"target_name": request.target_name},
                                 headers={"Authorization": f"Bearer {request.access_token}"
            })
        if response.status_code != 201:
            logging.debug(f"Failed to start recon: {response.json()} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)

        return StartReconResponse(response.json())

    def get_recon_event(self, request: GetEventRequest) -> ReceivedEvent:
        response = requests.post(self.get_events_url, json=request.model_dump_json(),
                              headers={"Authorization": f"Bearer {request.access_token}"})
        if response.status_code != 200:
            logging.debug(f"Failed to get recon events: {response.text} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)
        return ReceivedEvent.model_validate_json(response.json())

    def push_prompt_results(self, request: PushPromptRequest) -> PushPromptResultsResponse:
        response = requests.post(self.push_events_url, json=request.model_dump_json(),
                                 headers={"Authorization": f"Bearer {request.access_token}"})
        if response.status_code != 201:
            logging.debug(f"Failed to prompt results: {response.json()} - {response.status_code}")
            raise GuardrailServiceException(message=response.json(), status_code=response.status_code)

        return PushPromptResultsResponse.model_validate_json(response.json())
