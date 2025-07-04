import json

import requests_mock

from mindgard.recon.guardrail import GuardrailService, StartReconRequest


class TestReconGuardrailServiceStartRecon:
    def test_start_recon_guardrail_service(self):
        mock_url = "http://blah.co.uk"
        target_name = "blah"
        mock_return_id = "new-recon-id"
        user_sub = "user"

        guardrail_service = GuardrailService(url=mock_url)

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
