import pytest
import requests_mock

from src.mindgard.api_service import api_get
from src.mindgard.orchestrator import get_test_by_id, get_tests
from src.mindgard.constants import API_BASE
from unittest.mock import MagicMock

from typing import Dict, Any

from datetime import datetime
import json


def get_valid_attack_data(attack_id: str = "valid_id") -> Dict[str, Any]:
    return {
        "id": attack_id,
        "submitted_at": "2024-07-11T10:03:19.319654+00:00",
        "submitted_at_unix": 1720692199319.654,
        "run_at": "2024-07-11T10:03:22.180097+00:00",
        "run_at_unix": 1720692202180.0972,
        "state": 1,
        "state_message": "Completed",
        "runtime": 1.332952,
        "model": "cfp_faces_model",
        "dataset": "CFP",
        "attack": "SquareAttack",
        "risk": 60,
        "stacktrace": None,
    }


def get_valid_test_data(id: str = "valid_test_id", attack_id: str = "valid_id") -> Dict[str, Any]:
    return {
        "id": id,
        "mindgardModelName": "<model_name>",
        "source": "user",
        "createdAt": json.dumps(datetime.now(), default=str),
        "isCompleted": True,
        "hasFinished": True,
        "risk": 60,
        "attacks": [get_valid_attack_data(attack_id)],
    }


def test_get_all_tests(requests_mock: requests_mock.Mocker) -> None:
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()

    requests_mock.get(
        f"{API_BASE}/assessments?ungrouped=true",
        json=[get_valid_test_data(), get_valid_test_data()],
        status_code=200,
    )
    tests = get_tests(access_token=access_token, request_function=api_get)
    assert len(tests) == 2


def test_get_test_by_id(requests_mock: requests_mock.Mocker) -> None:
    test_id = "test_id"
    access_token = "valid_access_token"
    api_get.retry.sleep = MagicMock()

    requests_mock.get(
        f"{API_BASE}/assessments/{test_id}",
        json=get_valid_test_data(id=test_id),
        status_code=200,
    )
    test = get_test_by_id(
        test_id=test_id, access_token=access_token, request_function=api_get
    )

    assert test.id == test_id
    assert len(test.attacks) == 1


# def test_test_does_not_exist(requests_mock: requests_mock.Mocker) -> None:
#     test_id = 2
#     access_token = "valid_access_token"
#     api_get.retry.sleep = MagicMock()
#     requests_mock.get(f"{API_BASE}/assessments/{test_id}", status_code=404)
#     with pytest.raises(ValueError):
#         get_test_by_id(
#             test_id=test_id, access_token=access_token, request_function=api_get
#         )


# def test_get_attack_by_id(requests_mock: requests_mock.Mocker) -> None:
#     attack_id = 22
#     access_token = "valid_access_token"
#     api_get.retry.sleep = MagicMock()
#     requests_mock.get(
#         f"{DASHBOARD_URL}/r/attack/{attack_id}",
#         status_code=200,
#         json=get_valid_attack_data(),
#     )
#     attack = get_attack_by_id(
#         attack_id=attack_id, access_token=access_token, request_function=api_get
#     )
#     assert attack.state == 2  # asserts attack is completed(2)
#     assert attack.id == attack_id
#     assert attack.is_finished
#     assert attack.attack == "SquareAttack"


# def test_attack_does_not_exist(requests_mock: requests_mock.Mocker) -> None:
#     attack_id = 2
#     access_token = "valid_access_token"
#     api_get.retry.sleep = MagicMock()
#     requests_mock.get(f"{DASHBOARD_URL}/r/attack/{attack_id}", status_code=404)
#     with pytest.raises(ValueError):
#         get_attack_by_id(
#             attack_id=attack_id, access_token=access_token, request_function=api_get
#         )


# def test_attack_invalid_state(requests_mock: requests_mock.Mocker) -> None:
#     attack_id = 7
#     access_token = "valid_access_token"
#     api_get.retry.sleep = MagicMock()
#     requests_mock.get(
#         f"{DASHBOARD_URL}/r/attack/{attack_id}",
#         status_code=200,
#         json={"attack": "SquareAttack", "id": attack_id, "state": -2},
#     )
#     with pytest.raises(ValueError):
#         get_attack_by_id(
#             attack_id=attack_id, access_token=access_token, request_function=api_get
#         )
