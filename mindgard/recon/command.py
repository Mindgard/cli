import logging
from time import sleep
from typing import Protocol, Optional

from mindgard.auth import require_auth
from mindgard.exceptions import MGException
from mindgard.recon.guardrail import GuardrailService, StartReconRequest, GetEventRequest, ReceivedEvent, \
    AllowedEventTypes, PromptResult, PushPromptRequest, GetReconnRequest, GetReconnResponse
from mindgard.wrappers.llm import Context, PromptResponse

from dataclasses import dataclass


@dataclass
class OrchestratorSetupReconRequest:
    target_name: str


@dataclass
class OrchestratorSetupReconResponse:
    recon_id: str


@dataclass
class OrchestratorPollReconRequest:
    recon_id: str
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

    def start(self, orchestrator_setup_reconn_request: OrchestratorSetupReconRequest,
              access_token: str) -> OrchestratorSetupReconResponse:
        logging.debug(f"Starting guardrail reconnaissance for target: {orchestrator_setup_reconn_request.target_name}")
        response = self.service.start_recon(StartReconRequest(
            target_name=orchestrator_setup_reconn_request.target_name,
            access_token=access_token
        ))
        return OrchestratorSetupReconResponse(recon_id=response.id)

    def poll(self, orchestrator_poll_request: OrchestratorPollReconRequest,
             access_token: str) -> None:
        completed = False
        event: Optional[ReceivedEvent] = None

        logging.debug(f"Polling for prompt requests to process: {orchestrator_poll_request.recon_id}")
        while not completed:
            poll_iteration_result = self.poll_inner(orchestrator_poll_request, access_token)
            completed = poll_iteration_result.completed
            event = poll_iteration_result.event

            sleep(0.5)

        logging.debug(f"All prompt requests processed for recon_id: {orchestrator_poll_request.recon_id}")
        logging.debug("Fetching reconnaissance result...")
        reconn_result = self.fetch_recon_result(GetReconnRequest(recon_id=orchestrator_poll_request.recon_id, access_token=access_token))
        logging.debug(reconn_result)

    @dataclass
    class PollInner:
        completed: bool
        event: Optional[ReceivedEvent]

    def poll_inner(self, orchestrator_poll_request: OrchestratorPollReconRequest, access_token: str) -> PollInner:
        request = GetEventRequest(
            source_id=orchestrator_poll_request.recon_id,
            event_type=orchestrator_poll_request.types,
            access_token=access_token
        )

        event = self.service.get_recon_event(request)

        if event is None:
            return GuardrailReconnCommand.PollInner(completed=False, event=None)

        if event.event_type == 'prompt_request' and len(event.prompt_request) > 0:
            logging.debug(f"Processing prompt request")
            for request in event.prompt_request:
                response = None
                exception = None
                try:
                    response = self.call_system_under_test(request.prompt)
                except MGException as e:
                    logging.debug(f"Error communicating with target application: {e}")
                    exception = e

                content = response.response if response else None
                duration_ms = response.duration_ms if response else None
                error_code = None if exception is None else getattr(exception, "status_code", None)
                error_message = None if exception is None else str(exception)

                logging.debug(f"Pushing prompt result for request")
                self.service.push_prompt_results(
                    PushPromptRequest(
                        source_id=event.source_id,
                        event_type='prompt_result',
                        prompt_result=[PromptResult(
                            content=content,
                            duration_ms=duration_ms,
                            prompt_request=request,
                            error_code=error_code,
                            error_message=error_message
                        )],
                        access_token=access_token
                    )
                )

        if event.event_type == 'complete':
            logging.debug(f"Reconnaissance completed for recon_id: {orchestrator_poll_request.recon_id}")
            return GuardrailReconnCommand.PollInner(completed=True, event=event)
        else:
            return GuardrailReconnCommand.PollInner(completed=False, event=event)

    def fetch_recon_result(self, fetch_recon_request: GetReconnRequest) -> GetReconnResponse:
        response = self.service.get_recon_result(fetch_recon_request)
        return response
