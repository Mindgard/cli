from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

import requests


@dataclass
class StartReconRequest:
    target_name: str
    user_sub: str


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

class EventResponse(BaseModel):
    event_id: str
    event_type: str
    state: str
    reconn_id: str
    prompt_request: list[PromptRequest]

class GuardrailService:
    def __init__(self, reconn_url: str, get_events_url: str):
        self.reconn_url = reconn_url
        self.get_events_url = get_events_url

    def start_recon(self, request: StartReconRequest) -> StartReconResponse:
        response = requests.post(self.reconn_url,
                                 json={"target_name": request.target_name},
                                 headers={"x-mg-user": request.user_sub})
        return StartReconResponse(response.json())

    def get_recon_events(self, request: GetEventsRequest) -> EventResponse:
        event = requests.post(self.get_events_url, json=request.model_dump_json())
        return EventResponse.model_validate_json(event.json())

    def push_prompt_results(self):
        ...
