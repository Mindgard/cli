# import requests
from requests.exceptions import HTTPError
import requests_mock
import pytest
from ...src.mindgard.constants import API_BASE
from ...src.mindgard.api_service import ApiService

def test_submit_test(requests_mock: requests_mock.Mocker) -> None:
    svc = ApiService()
    requests_mock.post(f"{API_BASE}/assessments", text='{}', status_code=201)
    svc.submit_test("testtoken", "cfp_faces")

def test_submit_test_raises_failure(requests_mock: requests_mock.Mocker) -> None:
    svc = ApiService()
    requests_mock.post(f"{API_BASE}/assessments", text='{}', status_code=400)
    with pytest.raises(HTTPError):
        svc.submit_test("testtoken", "cfp_faces")