import pytest
import requests_mock

from ...src.mindgard.api_service import api_get
from ...src.mindgard.orchestrator import get_test_by_id, get_tests, submit_sandbox_test
from ...src.mindgard.constants import API_BASE
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


def get_valid_test_data(
    id: str = "valid_test_id", attack_id: str = "valid_id"
) -> Dict[str, Any]:
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


def test_submit_sandbox_test(requests_mock: requests_mock.Mocker) -> None:
    test_id = "valid_test_id"
    access_token = "valid_access_token"

    test_data = get_valid_test_data(id=test_id)

    requests_mock.post(
        f"{API_BASE}/assessments",
        json=test_data,
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/assessments/{test_id}",
        json=get_valid_test_data(id=test_id),
        status_code=200,
    )

    res = submit_sandbox_test(
        access_token=access_token, target_name=test_data["mindgardModelName"]
    )

    assert len(res.attacks) == len(test_data["attacks"])
    assert res.id == test_id
    assert res.mindgardModelName == test_data["mindgardModelName"]
