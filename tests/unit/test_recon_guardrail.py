import json

import pytest
import requests_mock
from pydantic_core._pydantic_core import ValidationError, SchemaError

from mindgard.recon.guardrail import GuardrailService, StartReconRequest, GetEventsRequest, ReceivedEvent, PushPromptRequest


class TestReconGuardrailServiceStartRecon:
    def test_start_recon_guardrail_service(self):
        mock_url = "http://blah.co.uk"
        target_name = "blah"
        mock_return_id = "new-recon-id"

        guardrail_service = GuardrailService(reconn_url=mock_url, get_events_url=mock_url, push_events_url=mock_url)

        start_recon_request = StartReconRequest(target_name=target_name)

        with requests_mock.Mocker() as m:
            mock_post = m.post(mock_url,
                               status_code=201,
                               json=mock_return_id)

            response = guardrail_service.start_recon(start_recon_request)

            assert mock_post.call_count == 1
            assert mock_post.request_history[0].method == "POST"
            assert mock_post.request_history[0].text == json.dumps({"target_name": target_name})

            assert response.id == mock_return_id


    def test_get_reconn_events_should_get_selected_events(self):
        events_url = "http://events.url"
        reconn_id = "new-recon-id"
        prompt_request = {
            "prompt": "hello",
            "sequence": 1,
            "language": "en",
            "is_malicious": False
        }

        expected_response = {
            "event_id": "new-prompt-request-event-id",
            "event_type": "prompt_request",
            "reconn_id": reconn_id,
            "prompt_request": [prompt_request]
        }

        event_request = GetEventsRequest(reconn_id=reconn_id, types=["prompt_request", "complete"])

        guardrail_service = GuardrailService(reconn_url=events_url, get_events_url=events_url, push_events_url=events_url)

        with requests_mock.Mocker() as m:
            mock_events = m.post(events_url, status_code=200, json=json.dumps(expected_response))
            events_response = guardrail_service.get_recon_events(event_request)

            assert mock_events.call_count == 1
            assert mock_events.request_history[0].method == "POST"
            assert mock_events.request_history[0].text == json.dumps(event_request.model_dump_json())
            assert ReceivedEvent.model_validate(expected_response) == events_response

    def test_get_reconn_events_should_raise_error_for_invalid_event_types(self):
        events_url = "http://events.url"
        reconn_id = "new-recon-id"

        with pytest.raises(Exception) as exc_info:

            event_request = GetEventsRequest(reconn_id=reconn_id, types=["prompt_result"])
            guardrail_service = GuardrailService(reconn_url=events_url, get_events_url=events_url, push_events_url=events_url)
            guardrail_service.get_recon_events(event_request)

        assert isinstance(exc_info.value, ValidationError)

    def test_push_prompt_results_should_push_target_response_to_reconn_guardrail_service(self):
        mock_url = "http://e"
        reconn_id = "new-recon-id"

        guardrail_service = GuardrailService(
            reconn_url=mock_url,
            get_events_url=mock_url,
            push_events_url=mock_url
        )

        push_prompt_request = {
            "reconn_id": reconn_id,
            "event_type": "prompt_result",
            "prompt_response": [
                {
                    "content": "response content",
                    "duration_ms": 100.0,
                    "prompt_request": {
                        "prompt": "hello",
                        "sequence": 1,
                        "language": "en",
                        "is_malicious": False
                    }
                }
            ]
        }

        expected_response = {
            "event_id": "new-prompt-result-event-id",
            "message": "event pushed successfully",
        }

        with requests_mock.Mocker() as m:
            mock_post = m.post(mock_url,
                               status_code=201,
                               json=json.dumps(expected_response))

            push_prompt_request_validated = PushPromptRequest.model_validate(push_prompt_request)
            response = guardrail_service.push_prompt_results(push_prompt_request_validated)

            assert mock_post.call_count == 1
            assert mock_post.request_history[0].method == "POST"
            assert mock_post.request_history[0].text == json.dumps(push_prompt_request_validated.model_dump_json())

            assert response.event_id == expected_response["event_id"]
            assert response.message == expected_response["message"]

