from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel

import requests


@dataclass
class StartReconRequest:
    target_name: str


@dataclass
class StartReconResponse:
    id: str

AllowedEventTypes = Literal['prompt_request', 'complete']
class GetEventsRequest(BaseModel):
    reconn_id: str
    types: list[AllowedEventTypes]

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

class PushPromptResultsResponse(BaseModel):
    event_id: str
    message: str

class GuardrailService:
    def __init__(self, reconn_url: str, get_events_url: str, push_events_url: str):
        self.reconn_url = reconn_url
        self.get_events_url = get_events_url
        self.push_events_url = push_events_url

    def start_recon(self, request: StartReconRequest) -> StartReconResponse:
        response = requests.post(self.reconn_url,
                                 json={"target_name": request.target_name})
        return StartReconResponse(response.json())

    def get_recon_events(self, request: GetEventsRequest) -> ReceivedEvent:
        event = requests.post(self.get_events_url, json=request.model_dump_json())
        if event.status_code != 200:
            raise Exception(f"Failed to get events: {event.text}")
        return ReceivedEvent.model_validate_json(event.json())

    def push_prompt_results(self, request: PushPromptRequest) -> PushPromptResultsResponse:
        response = requests.post(self.push_events_url, json=request.model_dump_json())
        if response.status_code != 201:
            raise Exception(f"Failed to prompt results: {response.text}")

        return PushPromptResultsResponse.model_validate_json(response.json())