import pytest
import requests_mock

from src.mindgard.api_service import api_get
from src.mindgard.orchestrator import get_test_by_id, get_attack_by_id
from src.mindgard.constants import API_BASE, DASHBOARD_URL
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
    assert len(test.attack_ids) > 0
    assert len(test.test_url) > 0
    print(test)


def test_test_does_not_exist(requests_mock: requests_mock.Mocker) -> None:
    test_id = "invalid_test_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()
    requests_mock.get(f"{API_BASE}/assessments?ungrouped=true", status_code=404)
    with pytest.raises(ValueError):
        get_test_by_id(
            test_id=test_id, access_token=access_token, request_function=api_get
        )


def test_get_attack_by_id(requests_mock: requests_mock.Mocker) -> None:
    attack_id = "valid_attack_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()
    requests_mock.get(
        f"{DASHBOARD_URL}/r/attack/{attack_id}",
        status_code=200,
        json={"attack": "SquareAttack", "id": attack_id, "state": 2},
    )
    attack = get_attack_by_id(
        attack_id=attack_id, access_token=access_token, request_function=api_get
    )
    assert attack.state == 2  # asserts attack is completed(2)
    assert attack.id == attack_id
    assert attack.is_finished
    assert attack.attack == "SquareAttack"


def test_attack_does_not_exist(requests_mock: requests_mock.Mocker) -> None:
    attack_id = "invalid_test_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()
    requests_mock.get(f"{DASHBOARD_URL}/r/attack/{attack_id}", status_code=404)
    with pytest.raises(ValueError):
        get_attack_by_id(
            attack_id=attack_id, access_token=access_token, request_function=api_get
        )


def test_attack_invalid_state(requests_mock: requests_mock.Mocker) -> None:
    attack_id = "valid_test_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()
    requests_mock.get(
        f"{DASHBOARD_URL}/r/attack/{attack_id}",
        status_code=200,
        json={"attack": "SquareAttack", "id": attack_id, "state": -2},
    )
    with pytest.raises(ValueError):
        get_attack_by_id(
            attack_id=attack_id, access_token=access_token, request_function=api_get
        )
