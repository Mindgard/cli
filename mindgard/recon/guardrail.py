from dataclasses import dataclass

import requests


@dataclass
class StartReconRequest:
    target_name: str
    user_sub: str


@dataclass
class StartReconResponse:
    id: str


class GuardrailService:
    def __init__(self, url: str):
        self.url = url

    def start_recon(self, request: StartReconRequest) -> StartReconResponse:
        response = requests.post(self.url,
                                 json={"target_name": request.target_name},
                                 headers={"x-mg-user": request.user_sub})
        return StartReconResponse(response.json())

    def get_recon_events(self):
        ...

    def push_prompt_results(self):
        ...
