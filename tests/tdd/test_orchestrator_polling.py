import pytest
import requests_mock

from ...src.mindgard.api_service import api_get
from ...src.mindgard.orchestrator import get_test_by_id
from ...src.mindgard.constants import API_BASE
from unittest.mock import MagicMock


def test_get_test_by_id(requests_mock: requests_mock.Mocker) -> None:
    test_id = "valid_test_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()

    test_data = {"url": "<some_url>", "attacks": [{"id": "<some_attack_id>"}]}

    requests_mock.get(
        f"{API_BASE}/assessments?ungrouped=true", json=test_data, status_code=200
    )
    test = get_test_by_id(
        test_id=test_id, access_token=access_token, request_function=api_get
    )
    assert len(test.attack_urls) > 0
    assert len(test.test_url) > 0
    print(test)


def test_does_not_exist(requests_mock: requests_mock.Mocker) -> None:
    test_id = "invalid_test_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()
    requests_mock.get(f"{API_BASE}/assessments?ungrouped=true", status_code=404)
    with pytest.raises(ValueError):
        get_test_by_id(
            test_id=test_id, access_token=access_token, request_function=api_get
        )


def test_test_model_is_valid() -> None:
    pass


def test_test_model_is_invalid() -> None:
    pass


def test_test_is_finished() -> None:
    pass


def test_test_is_not_finished() -> None:
    pass
