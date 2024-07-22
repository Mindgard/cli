import pytest

from src.mindgard.api_service import api_post, api_get

from typing import Dict, Any

import requests_mock
from requests.exceptions import HTTPError

from unittest.mock import MagicMock


def get_valid_request_inputs() -> Dict[str, Any]:
    return {
        "payload": {"key": "value"},
        "access_token": "token",
        "url": "http://api.sandbox.mindgard.com",
    }


def test_post_request_success(requests_mock: requests_mock.Mocker) -> None:
    inputs = get_valid_request_inputs()
    requests_mock.post(inputs["url"], json=inputs["payload"], status_code=200)
    resp = api_post(**inputs)

    assert resp is not None
    assert resp.json() is not None
    assert resp.json() == inputs["payload"]


@pytest.mark.parametrize("status_code", [(404), (400), (500), (401), (403)])
def test_post_request_raises_http_error(
    requests_mock: requests_mock.Mocker, status_code: int
) -> None:
    # overrides the sleep function so these tests pass quicker
    api_post.retry.sleep = MagicMock()
    inputs = get_valid_request_inputs()
    requests_mock.post(inputs["url"], json=inputs["payload"], status_code=status_code)
    with pytest.raises(HTTPError):
        api_post(**inputs)


def test_post_request_retries_after_failure(
    requests_mock: requests_mock.Mocker,
) -> None:
    api_post.retry.sleep = MagicMock()
    inputs = get_valid_request_inputs()
    requests_mock.post(
        url=inputs["url"],
        response_list=[
            {"json": {"some": "data"}, "status_code": 400},
            {"json": {"some": "data"}, "status_code": 400},
            {"json": {"some": "data"}, "status_code": 200},
            {"json": {"some": "data"}, "status_code": 200},
        ],
    )

    api_post(**inputs)
    assert api_post.retry.statistics["attempt_number"] == 3


def test_get_request_success(requests_mock: requests_mock.Mocker) -> None:
    inputs = get_valid_request_inputs()
    requests_mock.get(inputs["url"], json=inputs["payload"], status_code=200)
    resp = api_get(inputs["url"], inputs["access_token"])

    assert resp is not None
    assert resp.json() is not None
    assert resp.json() == inputs["payload"]


@pytest.mark.parametrize("status_code", [(404), (400), (500), (401), (403)])
def test_get_request_raises_http_error(
    requests_mock: requests_mock.Mocker, status_code: int
) -> None:
    # overrides the sleep function so these tests pass quicker
    api_get.retry.sleep = MagicMock()
    inputs = get_valid_request_inputs()
    requests_mock.get(inputs["url"], json=inputs["payload"], status_code=status_code)
    with pytest.raises(HTTPError):
        resp = api_get(inputs["url"], inputs["access_token"])


def test_get_request_retries_after_failure(
    requests_mock: requests_mock.Mocker,
) -> None:
    api_get.retry.sleep = MagicMock()
    inputs = get_valid_request_inputs()
    requests_mock.get(
        url=inputs["url"],
        response_list=[
            {"json": {"some": "data"}, "status_code": 400},
            {"json": {"some": "data"}, "status_code": 400},
            {"json": {"some": "data"}, "status_code": 200},
            {"json": {"some": "data"}, "status_code": 200},
        ],
    )

    resp = api_get(inputs["url"], inputs["access_token"])
    assert api_get.retry.statistics["attempt_number"] == 3
