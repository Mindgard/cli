import platform
from unittest.mock import MagicMock

from ...src.mindgard.run_functions.external_models import model_test_output_factory
from ...src.mindgard import auth
import pytest
from pytest_snapshot.plugin import Snapshot
# from typing import NamedTuple
# from unittest.mock import MagicMock
from ...src.mindgard.constants import API_BASE
from ...src.mindgard.run_functions.sandbox_test import submit_sandbox_polling, submit_sandbox_submit_factory
from ...src.mindgard.run_poll_display import cli_run
from ...src.mindgard.utils import convert_test_to_cli_response
import requests_mock # type: ignore

def test_json_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot, requests_mock: requests_mock.Mocker) -> None:
    # fixture = _helper_fixtures()

    auth.load_access_token = MagicMock(return_value="atoken")

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": "test_id",
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/assessments/test_id",
        json={
            "id": "test_id",
            "mindgardModelName": "mistral",
            "source": "mindgard",
            "createdAt": "2021-09-01T00:00:00.000Z",
            "attacks": [
                {
                    "id": "example_id",
                    "submitted_at": "2021-09-01T00:00:00.000Z",
                    "submitted_at_unix": 1630454400.0,
                    "run_at": "2021-09-01T00:00:00.000Z",
                    "run_at_unix": 1630454400.0,
                    "state": 2,
                    "state_message": "Running",
                    "runtime": 10.5,
                    "model": "mymodel",
                    "dataset": "mydataset",
                    "attack": "myattack",
                    "risk": 12,
                    "stacktrace": None,        
                }
            ],
            "isCompleted": True,
            "hasFinished": True,
            "risk": 13,
        },
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory(model_name="mistral")
    submit_sandbox_output = model_test_output_factory(risk_threshold=100)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=True)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=100)

    assert res.code() == 0
    captured = capsys.readouterr()
    stdout = captured.out
    snapshot.assert_match(stdout, 'stdout.json')

def test_text_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot, requests_mock: requests_mock.Mocker) -> None:
    auth.load_access_token = MagicMock(return_value="atoken")

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": "test_id",
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/assessments/test_id",
        json={
            "id": "test_id",
            "mindgardModelName": "mistral",
            "source": "mindgard",
            "createdAt": "2021-09-01T00:00:00.000Z",
            "attacks": [
                {
                    "id": "example_id",
                    "submitted_at": "2021-09-01T00:00:00.000Z",
                    "submitted_at_unix": 1630454400.0,
                    "run_at": "2021-09-01T00:00:00.000Z",
                    "run_at_unix": 1630454400.0,
                    "state": 2,
                    "state_message": "Running",
                    "runtime": 10.5,
                    "model": "mymodel",
                    "dataset": "mydataset",
                    "attack": "myattack",
                    "risk": 12,
                    "stacktrace": None,        
                }
            ],
            "isCompleted": True,
            "hasFinished": True,
            "risk": 13,
        },
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory(model_name="mistral")
    submit_sandbox_output = model_test_output_factory(risk_threshold=100)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=False)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=100)

    assert res.code() == 0
    captured = capsys.readouterr()
    stdout = captured.out

    if platform.system() == "Windows":
        # TODO: this is a basic check as Rich renders differently on windows
        assert f"Results - https://sandbox.mindgard.ai/r/test/test_id" in stdout
        assert "Attack myattack done success" in stdout
    else:
        snapshot.assert_match(stdout, 'stdout.txt')

@pytest.mark.parametrize("risk_score,risk_threshold,exit_code", [(49, 50, 0), (50, 49, 1)])
def test_risk_threshold(risk_score: int, risk_threshold: int, exit_code: int, requests_mock: requests_mock.Mocker) -> None:
    auth.load_access_token = MagicMock(return_value="atoken")

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": "test_id",
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/assessments/test_id",
        json={
            "id": "test_id",
            "mindgardModelName": "mistral",
            "source": "mindgard",
            "createdAt": "2021-09-01T00:00:00.000Z",
            "attacks": [
                {
                    "id": "example_id",
                    "submitted_at": "2021-09-01T00:00:00.000Z",
                    "submitted_at_unix": 1630454400.0,
                    "run_at": "2021-09-01T00:00:00.000Z",
                    "run_at_unix": 1630454400.0,
                    "state": 2,
                    "state_message": "Running",
                    "runtime": 10.5,
                    "model": "mymodel",
                    "dataset": "mydataset",
                    "attack": "myattack",
                    "risk": 12,
                    "stacktrace": None,        
                }
            ],
            "isCompleted": True,
            "hasFinished": True,
            "risk": risk_score,
        },
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory(model_name="mistral")
    submit_sandbox_output = model_test_output_factory(risk_threshold=risk_threshold)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=False)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=risk_threshold)

    assert res.code() == exit_code