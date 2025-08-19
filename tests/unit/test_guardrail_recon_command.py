from unittest.mock import MagicMock, call
import pytest
from mindgard.exceptions import MGException
from mindgard.recon.command import GuardrailReconnCommand, OrchestratorSetupReconRequest, ICallLLM, \
    OrchestratorPollReconRequest
from mindgard.recon.guardrail import GuardrailService, StartReconResponse, ReceivedEvent, PromptRequest, \
    AllowedEventTypes, PushPromptResultsResponse, PushPromptRequest, PromptResult, GuardrailServiceException, \
    GetReconnResponse, ReconnResult, GetReconnRequest
from mindgard.wrappers.llm import PromptResponse

class TestGuardrailReconnCommand:
    def test_start_command(self):

        recon_id = "mock-recon-id"
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_guardrail_service.start_recon = MagicMock(return_value=StartReconResponse(id=recon_id))


        command = GuardrailReconnCommand(call_system_under_test=MagicMock(spec=ICallLLM), service=mock_guardrail_service)
        request = OrchestratorSetupReconRequest(target_name="test-target")

        assert command.start(request, access_token="blah").recon_id == recon_id

    def test_poll_inner_successfully_processes_an_event(self):
        source_id = "mock-recon-id"
        access_token = "mock-access-token"
        types: list[AllowedEventTypes] = ["prompt_request", "complete"]
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_llm_call = MagicMock(spec=ICallLLM, return_value=PromptResponse(
            prompt="test prompt",
            response="mock response",
            duration_ms=100.0
        ))
        mock_guardrail_service.get_recon_event = MagicMock(side_effect=[
            ReceivedEvent(
                event_id="event-id",
                event_type="prompt_request",
                source_id=source_id,
                prompt_request=[
                    PromptRequest(
                        prompt="test prompt",
                        language="en",
                    ),
                    PromptRequest(
                        prompt="test prompt 2",
                        language="en",
                    )
                ]
            ),
            ReceivedEvent(
                event_id="complete-event-id",
                event_type="complete",
                source_id=source_id,
                prompt_request=[]
            )
        ])

        mock_guardrail_service.push_prompt_results = MagicMock(return_value=PushPromptResultsResponse(
            event_id="push-event-id",
        ))

        command = GuardrailReconnCommand(call_system_under_test=mock_llm_call, service=mock_guardrail_service)

        poll_inner_response = command.poll_inner(
            orchestrator_poll_request=OrchestratorPollReconRequest(recon_id=source_id, types=types),
            access_token=access_token
        )
        assert poll_inner_response.completed == False
        assert poll_inner_response.event.event_type == "prompt_request"

        assert mock_guardrail_service.get_recon_event.call_count == 1
        assert mock_llm_call.call_count == 2
        assert mock_guardrail_service.push_prompt_results.call_count == 2

        poll_inner_response = command.poll_inner(
            orchestrator_poll_request=OrchestratorPollReconRequest(recon_id=source_id, types=types),
            access_token=access_token
        )

        assert poll_inner_response.completed == True
        assert poll_inner_response.event.event_type == "complete"

        assert mock_llm_call.call_count == 2
        assert mock_guardrail_service.push_prompt_results.call_count == 2
        assert mock_guardrail_service.get_recon_event.call_count == 2

    def test_poll_inner_call_system_under_test_raises_exception(self):
        source_id = "mock-recon-id"
        access_token = "mock-access-token"
        types: list[AllowedEventTypes] = ["prompt_request", "complete"]
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_llm_call = MagicMock(spec=ICallLLM, side_effect=[MGException("Unable to call system under test"), MGException("Unable to call system under test")])
        mock_guardrail_service.get_recon_event = MagicMock(side_effect=[
            ReceivedEvent(
                event_id="event-id",
                event_type="prompt_request",
                source_id=source_id,
                prompt_request=[
                    PromptRequest(
                        prompt="test prompt",
                        language="en",
                    ),
                    PromptRequest(
                        prompt="test prompt 2",
                        language="en",
                    )
                ]
            ),
            ReceivedEvent(
                event_id="complete-event-id",
                event_type="complete",
                source_id=source_id,
                prompt_request=[]
            )
        ])

        mock_guardrail_service.push_prompt_results = MagicMock(return_value=PushPromptResultsResponse(
            event_id="push-event-id",
        ))

        command = GuardrailReconnCommand(call_system_under_test=mock_llm_call, service=mock_guardrail_service)

        poll_inner_response = command.poll_inner(
            orchestrator_poll_request=OrchestratorPollReconRequest(recon_id=source_id, types=types),
            access_token=access_token
        )

        assert poll_inner_response.completed == False
        assert mock_guardrail_service.push_prompt_results.call_count == 2
        assert mock_guardrail_service.push_prompt_results.call_args_list == [
            call(
                PushPromptRequest(
                    source_id=source_id,
                    event_type='prompt_result',
                    prompt_result=[
                        PromptResult(
                            content=None,
                            duration_ms=None,
                            prompt_request=PromptRequest(
                                prompt="test prompt",
                                language="en",
                            ),
                            error_code=None,
                            error_message="Unable to call system under test"
                        )
                    ],
                    access_token=access_token
                )
            ),
            call(
                PushPromptRequest(
                    source_id=source_id,
                    event_type='prompt_result',
                    prompt_result=[
                        PromptResult(
                            content=None,
                            duration_ms=None,
                            prompt_request=PromptRequest(
                                prompt="test prompt 2",
                                language="en",
                            ),
                            error_code=None,
                            error_message="Unable to call system under test"
                        )
                    ],
                    access_token=access_token
                )
            )
        ]

    def test_poll_inner_push_prompt_results_raises_exception(self):
        source_id = "mock-recon-id"
        access_token = "mock-access-token"
        types: list[AllowedEventTypes] = ["prompt_request", "complete"]
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_llm_call = MagicMock(spec=ICallLLM, return_value=PromptResponse(
            prompt="test prompt",
            response="mock response",
            duration_ms=100.0
        ))
        mock_guardrail_service.get_recon_event = MagicMock(side_effect=[
            ReceivedEvent(
                event_id="event-id",
                event_type="prompt_request",
                source_id=source_id,
                prompt_request=[
                    PromptRequest(
                        prompt="test prompt",
                        language="en",
                    ),
                    PromptRequest(
                        prompt="test prompt 2",
                        language="en",
                    )
                ]
            ),
            ReceivedEvent(
                event_id="complete-event-id",
                event_type="complete",
                source_id=source_id,
                prompt_request=[]
            )
        ])

        with pytest.raises(Exception) as exception:
            mock_guardrail_service.push_prompt_results = MagicMock(side_effect=[
                GuardrailServiceException("Error pushing prompt results", status_code=500)])

            command = GuardrailReconnCommand(call_system_under_test=mock_llm_call, service=mock_guardrail_service)

            command.poll_inner(
                orchestrator_poll_request=OrchestratorPollReconRequest(recon_id=source_id, types=types),
                access_token=access_token
            )

        assert isinstance(exception.value, GuardrailServiceException)

    def test_poll_command(self):
        source_id = "uuid-recon-id"
        types: list[AllowedEventTypes] = ["prompt_request", "complete"]
        prompt_request_event = ReceivedEvent(
            event_id="event-id",
            event_type="prompt_request",
            source_id=source_id,
            prompt_request=[
                PromptRequest(
                    prompt="test prompt",
                    language="en",
                ),
                PromptRequest(
                    prompt="another test prompt",
                    language="en",
                )
            ]
        )

        complete_event = ReceivedEvent(
            event_id="complete-event-id",
            event_type="complete",
            source_id=source_id,
            prompt_request=[]
        )

        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_guardrail_service.get_recon_event = MagicMock(side_effect=[prompt_request_event, complete_event])
        mock_guardrail_service.push_prompt_results = MagicMock(return_value=PushPromptResultsResponse(
            event_id="push-event-id",
        ))

        mock_llm_call = MagicMock(spec=ICallLLM, return_value=PromptResponse(
            prompt="test prompt",
            response="mock response",
            duration_ms=100.0
        ))

        command = GuardrailReconnCommand(call_system_under_test=mock_llm_call, service=mock_guardrail_service)

        request = OrchestratorPollReconRequest(recon_id=source_id, types=types)

        command.poll(request, access_token="test-access-token")

        assert mock_llm_call.call_count == 2
        assert mock_guardrail_service.get_recon_event.call_count == 2
        assert mock_guardrail_service.push_prompt_results.call_count == 2

    def test_fetch_recon_result_command(self):

        recon_id = "mock-recon-id"
        recon_result =ReconnResult(
            guardrail_detected=True,
            detected_guardrails=["y-guard", "x-guard"]
        )
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_guardrail_service.get_recon_result = MagicMock(return_value=GetReconnResponse(
            id=recon_id,
            state="completed",
            result=recon_result,
            target_name="test-target"
        ))


        command = GuardrailReconnCommand(call_system_under_test=MagicMock(spec=ICallLLM), service=mock_guardrail_service)
        request = GetReconnRequest(recon_id=recon_id, access_token="blah")

        assert command.fetch_recon_result(request).id == recon_id
