import requests
import requests_mock
from ...src.mindgard.constants import API_BASE
from ...src.mindgard.api_service import ApiService

def test_submit_test(requests_mock: requests_mock.Mocker) -> None:
    svc = ApiService()
    requests_mock.post('https://api.sandbox.mindgard.ai/api/v1/assessments', text='{}', status_code=201)

    ret = svc.submit_test("testtoken", "cfp_faces")

    # assert ret["mindgardModelName"] == "cfp_faces"
    # requests_mock.post()