import json

import pytest
import requests_mock
from pydantic_core._pydantic_core import ValidationError, SchemaError

from mindgard.recon.guardrail import GuardrailService, StartReconRequest, GetEventRequest, ReceivedEvent, \
    PushPromptRequest, GuardrailServiceException, GetReconnRequest, GetReconnResponse, PromptResult, PromptRequest


class TestReconGuardrailServiceStartRecon:
    def test_start_recon_guardrail_service(self):
        mock_url = "http://blah.co.uk"
        target_name = "blah"
        mock_return_response = {
            "recon_id": "new-recon-id",
        }
        access_token = "<BEARER_TOKEN>"

        guardrail_service = GuardrailService(
            reconn_url=mock_url, get_events_url=mock_url, push_events_url=mock_url)

        start_recon_request = StartReconRequest(target_name=target_name, access_token=access_token)

        with requests_mock.Mocker() as m:
            mock_post = m.post(mock_url,
                               status_code=201,
                               json=mock_return_response)

            response = guardrail_service.start_recon(start_recon_request)

            assert mock_post.call_count == 1
            assert mock_post.request_history[0].method == "POST"
            assert mock_post.request_history[0].text == json.dumps({"target_name": target_name})
            assert mock_post.request_history[0].headers["Authorization"] == f"Bearer {access_token}"

            assert response.id == mock_return_response.get("recon_id")

    def test_start_recon_guardrail_service_returns_exception(self):
        mock_url = "http://blah.co.uk"
        target_name = "blah"
        mock_return_id = "new-recon-id"
        access_token = "<BEARER_TOKEN>"

        guardrail_service = GuardrailService(
            reconn_url=mock_url, get_events_url=mock_url, push_events_url=mock_url)

        start_recon_request = StartReconRequest(target_name=target_name, access_token=access_token)

        with pytest.raises(GuardrailServiceException) as exc_info:
            with requests_mock.Mocker() as m:
                m.post(mock_url,
                       status_code=500,
                       json={"detail": "Internal Server Error"})

                guardrail_service.start_recon(start_recon_request)

        assert isinstance(exc_info.value, GuardrailServiceException)
        assert exc_info.value.status_code == 500
        assert exc_info.value.message == {"detail": "Internal Server Error"}

    def test_get_reconn_events_should_get_selected_events(self):
        events_url = "http://events.url"
        source_id = "new-recon-id"
        access_token = "<BEARER_TOKEN>"
        prompt_request = {
            "prompt": "hello",
            "sequence": 1,
            "language": "en",
            "is_malicious": False
        }

        expected_response = {
            "event_id": "new-prompt-request-event-id",
            "event_type": "prompt_request",
            "source_id": source_id,
            "prompt_request": [prompt_request]
        }

        event_request = GetEventRequest(
            source_id=source_id,
            event_type=["prompt_request", "complete"],
            access_token=access_token
        )

        guardrail_service = GuardrailService(
            reconn_url=events_url,
            get_events_url=events_url,
            push_events_url=events_url
        )

        with requests_mock.Mocker() as m:
            mock_events = m.post(events_url, status_code=200, json=expected_response)
            events_response = guardrail_service.get_recon_event(event_request)

            assert mock_events.call_count == 1
            assert mock_events.request_history[0].method == "POST"
            expected_payload = event_request.model_dump()
            expected_payload.pop("access_token", None)
            assert mock_events.request_history[0].json() == expected_payload
            assert mock_events.request_history[0].headers["Authorization"] == f"Bearer {access_token}"
            assert ReceivedEvent.model_validate(expected_response) == events_response

    def test_get_reconn_events_should_return_none_for_invalid_reconn_id(self):
        events_url = "http://events.url"
        recon_id = "invalid-recon-id"
        access_token = "<BEARER_TOKEN>"
        event_request = GetEventRequest(
            source_id=recon_id,
            event_type=["prompt_request", "complete"],
            access_token=access_token
        )
        guardrail_service = GuardrailService(
            reconn_url=events_url,
            get_events_url=events_url,
            push_events_url=events_url
        )
        with requests_mock.Mocker() as m:
            m.post(events_url, status_code=404, json={"detail": "Recon ID not found"})
            events_response = guardrail_service.get_recon_event(event_request)
            assert events_response is None

    def test_get_reconn_events_should_raise_error_if_service_receives_non_404_or_200_response(self):
        events_url = "http://events.url"
        recon_id = "invalid-recon-id"
        access_token = "<BEARER_TOKEN>"
        event_request = GetEventRequest(
            source_id=recon_id,
            event_type=["prompt_request", "complete"],
            access_token=access_token
        )
        guardrail_service = GuardrailService(
            reconn_url=events_url,
            get_events_url=events_url,
            push_events_url=events_url
        )
        with pytest.raises(Exception) as exc_info:
            with requests_mock.Mocker() as m:
                m.post(events_url, status_code=500, json={"detail": "something went wrong"})
                guardrail_service.get_recon_event(event_request)
        assert isinstance(exc_info.value, Exception)

    def test_get_reconn_events_should_raise_error_for_invalid_event_types(self):
        reconn_id = "new-recon-id"
        access_token = "<BEARER_TOKEN>"

        with pytest.raises(Exception) as exc_info:
            GetEventRequest(reconn_id=reconn_id, event_type=["prompt_result"], access_token=access_token)

        assert isinstance(exc_info.value, ValidationError)

    def test_push_prompt_results_should_push_target_response_to_reconn_guardrail_service(self):
        mock_url = "http://e"
        source_id = "new-source-id"
        access_token = "<BEARER_TOKEN>"

        guardrail_service = GuardrailService(
            reconn_url=mock_url,
            get_events_url=mock_url,
            push_events_url=mock_url,
        )

        push_prompt_request = PushPromptRequest(
            source_id=source_id,
            event_type="prompt_result",
            prompt_result=[PromptResult(
                content="response content",
                duration_ms=100.0,
                prompt_request=PromptRequest(
                    prompt="hello",
                    sequence=1,
                    language="en",
                    is_malicious=False
                )
            )],
            access_token=access_token
        )

        expected_response = {
            "event_id": "new-prompt-result-event-id",
        }

        with requests_mock.Mocker() as m:
            mock_post = m.post(mock_url,
                               status_code=201,
                               json=expected_response)

            response = guardrail_service.push_prompt_results(push_prompt_request)

            expected_request = push_prompt_request.to_api_request()

            assert mock_post.call_count == 1
            assert mock_post.request_history[0].method == "POST"
            assert mock_post.request_history[0].headers["Authorization"] == f"Bearer {access_token}"
            assert mock_post.request_history[0].json() == expected_request

            assert response.event_id == expected_response["event_id"]

    def test_push_prompt_results_should_raise_error_for_invalid_request(self):
        mock_url = "http://e"
        source_id = "new-recon-id"
        access_token = "<BEARER_TOKEN>"
        guardrail_service = GuardrailService(
            reconn_url=mock_url,
            get_events_url=mock_url,
            push_events_url=mock_url,
        )
        push_prompt_request = PushPromptRequest(
            source_id=source_id,
            event_type="prompt_result",
            prompt_result=[PromptResult(
                content="response content",
                duration_ms=100.0,
                prompt_request=PromptRequest(
                    prompt="hello",
                    sequence=1,
                    language="en",
                    is_malicious=False
                )
            )],
            access_token=access_token
        )

        with pytest.raises(Exception) as exc_info:
            with requests_mock.Mocker() as m:
                m.post(mock_url, status_code=400, json={"detail": "Bad Request"})
                guardrail_service.push_prompt_results(push_prompt_request)

        assert isinstance(exc_info.value, GuardrailServiceException)
        assert exc_info.value.status_code == 400
        assert exc_info.value.message == {"detail": "Bad Request"}

    def test_get_reconn_result_should_get_final_reconn_result(self):
        recon_url = "http://recon.url"
        recon_id = "new-recon-id"
        access_token = "<BEARER_TOKEN>"

        result = {
            "guardrail_detected": True,
            "detected_guardrails": ["y-guard", "x-guard"],
        }

        expected_response = {
            "id": "new-prompt-request-event-id",
            "state": "COMPLETED",
            "result": result,
            "reason": "We suspect presence of a guardrail",
            "target_name": "target-name"
        }

        reconn_request = GetReconnRequest(recon_id=recon_id, access_token=access_token)

        guardrail_service = GuardrailService(reconn_url=recon_url, get_events_url=recon_url,
                                             push_events_url=recon_url)

        with requests_mock.Mocker() as m:
            mock_events = m.get(f"{recon_url}", status_code=200, json=expected_response)
            reconn_response = guardrail_service.get_recon_result(reconn_request)

            assert mock_events.call_count == 1

            req = mock_events.request_history[0]
            assert req.qs['recon_id'] == [recon_id]

            assert mock_events.request_history[0].method == "GET"
            assert mock_events.request_history[0].headers["Authorization"] == f"Bearer {access_token}"
            assert GetReconnResponse.model_validate(expected_response) == reconn_response
