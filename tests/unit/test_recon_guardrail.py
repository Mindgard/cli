import json

import pytest
import requests_mock
from pydantic_core._pydantic_core import ValidationError, SchemaError

from mindgard.recon.guardrail import GuardrailService, StartReconRequest, GetEventsRequest, EventResponse


class TestReconGuardrailServiceStartRecon:
    def test_start_recon_guardrail_service(self):
        mock_url = "http://blah.co.uk"
        target_name = "blah"
        mock_return_id = "new-recon-id"
        user_sub = "user"

        guardrail_service = GuardrailService(reconn_url=mock_url, get_events_url=mock_url)

        start_recon_request = StartReconRequest(target_name=target_name,
                                                user_sub=user_sub)

        with requests_mock.Mocker() as m:
            mock_post = m.post(mock_url,
                               status_code=201,
                               json=mock_return_id)

            response = guardrail_service.start_recon(start_recon_request)

            assert mock_post.call_count == 1
            assert mock_post.request_history[0].method == "POST"
            assert mock_post.request_history[0].text == json.dumps({"target_name": target_name})
            assert mock_post.request_history[0].headers["x-mg-user"] == user_sub

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
            "state": "RUNNABLE",
            "reconn_id": reconn_id,
            "prompt_request": [prompt_request]
        }

        event_request = GetEventsRequest(reconn_id=reconn_id, types=["prompt_request", "complete"])

        guardrail_service = GuardrailService(reconn_url=events_url, get_events_url=events_url)

        with requests_mock.Mocker() as m:
            mock_events = m.post(events_url, status_code=200, json=json.dumps(expected_response))
            events_response = guardrail_service.get_recon_events(event_request)

            assert mock_events.call_count == 1
            assert mock_events.request_history[0].method == "POST"
            assert mock_events.request_history[0].text == json.dumps(event_request.model_dump_json())
            assert EventResponse.model_validate(expected_response) == events_response

    def test_get_reconn_events_should_raise_error_for_invalid_event_types(self):
        events_url = "http://events.url"
        reconn_id = "new-recon-id"

        with pytest.raises(Exception) as exc_info:

            event_request = GetEventsRequest(reconn_id=reconn_id, types=["prompt_result"])
            guardrail_service = GuardrailService(reconn_url=events_url, get_events_url=events_url)
            guardrail_service.get_recon_events(event_request)

        assert isinstance(exc_info.value, ValidationError)
