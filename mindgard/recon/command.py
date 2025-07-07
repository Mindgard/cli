from typing import Protocol, Optional

from mindgard.auth import require_auth
from mindgard.recon.guardrail import GuardrailService, StartReconRequest, GetEventRequest, ReceivedEvent, \
    AllowedEventTypes
from mindgard.utils import parse_toml_and_args_into_final_args
from mindgard.wrappers.llm import LLMModelWrapper, Context, PromptResponse
from mindgard.wrappers.utils import parse_args_into_model
from dataclasses import dataclass

@dataclass
class OrchestratorSetupReconRequest:
    target_name: str

@dataclass
class OrchestratorSetupReconResponse:
    id: str

@dataclass
class OrchestratorPollReconRequest:
    reconn_id: str
    types: list[AllowedEventTypes]

@dataclass
class OrchestratorPollReconResponse:
    events: list[ReceivedEvent]

class ICallLLM(Protocol):
    def __call__(self, content: str, with_context: Optional[Context] = None) -> PromptResponse:
        ...

class GuardrailReconnCommand:
    def __init__(self, call_system_under_test: ICallLLM, service: GuardrailService):
        self.call_system_under_test = call_system_under_test
        self.service = service

    @require_auth
    def start(self, orchestrator_setup_reconn_request: OrchestratorSetupReconRequest,
              access_token: str) -> OrchestratorSetupReconResponse:
        return self._start(orchestrator_setup_reconn_request, access_token)

    def _start(self, orchestrator_setup_reconn_request: OrchestratorSetupReconRequest,
               access_token: str) -> OrchestratorSetupReconResponse:
        response = self.service.start_recon(StartReconRequest(
            target_name=orchestrator_setup_reconn_request.target_name,
            access_token=access_token
        ))
        return OrchestratorSetupReconResponse(id=response.id)

    @require_auth
    def poll(self, orchestrator_poll_request: OrchestratorPollReconRequest,
             access_token: str) -> OrchestratorPollReconResponse:
        return self._poll(orchestrator_poll_request, access_token)

    def _poll(self, orchestrator_poll_request: OrchestratorPollReconRequest,
              access_token: str) -> OrchestratorPollReconResponse:
        completed = False
        while not completed:
            completed = self.poll_inner(orchestrator_poll_request, access_token)

    def poll_inner(self, orchestrator_poll_request: OrchestratorPollReconRequest, access_token: str) -> bool:
        request = GetEventRequest(
            reconn_id=orchestrator_poll_request.reconn_id,
            types=orchestrator_poll_request.types,
            access_token=access_token
        )

        event = self.service.get_recon_event(request)

        # if event.event_type == 'prompt_request':


        if event.event_type == 'complete':
            return True
        else:
            return False