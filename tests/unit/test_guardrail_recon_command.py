import dataclasses
from unittest.mock import MagicMock

from mindgard.recon.command import GuardrailReconnCommand, OrchestratorSetupReconRequest, ICallLLM
from mindgard.recon.guardrail import GuardrailService, StartReconResponse, ReceivedEvent, PromptRequest


# mock_call_system_under_test = MagicMock(return_value=PromptResponse(prompt="Hello", response="it's me", duration_ms=30.0))

# @dataclasses.dataclass
# class START_COMMAND_TEST_CASE:
#     target_name: str
#     access_token: str
#
# TEST_CASES = [
#     START_COMMAND_TEST_CASE(target_name="test-target", access_token="test")
# ]
# def test_start_command_blah(self):
#     pass

class TestGuardrailReconnCommand:
    def test_start_command(self):

        recon_id = "mock-recon-id"
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        mock_guardrail_service.start_recon = MagicMock(return_value=StartReconResponse(id=recon_id))


        command = GuardrailReconnCommand(call_system_under_test=MagicMock(spec=ICallLLM), service=mock_guardrail_service)
        request = OrchestratorSetupReconRequest(target_name="test-target")

        assert command._start(request, access_token="blah").id == recon_id

    def test_poll_command(self):
        recon_id = "uuid-recon-id"
        types = ['prompt_request', 'complete']
        mock_guardrail_service = MagicMock(spec=GuardrailService)
        received_event = ReceivedEvent(
            event_id="event-id",
            event_type="prompt_request",
            reconn_id=recon_id,
            prompt_request=[
                PromptRequest(
                    prompt="test prompt",
                    sequence=1,
                    language="en",
                    is_malicious=False
                ),
                PromptRequest(
                    prompt="another test prompt",
                    sequence=2,
                    language="en",
                    is_malicious=True
                )
            ]
        )
        mock_guardrail_service.get_recon_event = MagicMock()


# Fetch list of events
# If event_type is prompt_request
# Loop through prompt_request list
# # Call model with prompt
# # Get response from model
# # Create a new prompt_result event with response
# # Else if event_type if complete
# # stop polling