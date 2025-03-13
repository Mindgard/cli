from unittest.mock import MagicMock

from mindgard.run_functions.external_models import model_test_output_factory
from mindgard import auth
import pytest
from pytest_snapshot.plugin import Snapshot
from mindgard.constants import API_BASE
from mindgard.run_functions.sandbox_test import submit_sandbox_polling, submit_sandbox_submit_factory
from mindgard.run_poll_display import cli_run
from mindgard.utils import convert_test_to_cli_response
import requests_mock # type: ignore

def build_slightly_different_test_response(test_id: str, flagged_events: int = 0, total_events: int = 0):
    return {
        "id": test_id,
        "created_at": "2025-03-1215:34:00.50528",
        "source": "user",
        "model_name": "<model_name>",
        "has_finished": True,
        "total_events": total_events,
        "flagged_events": flagged_events,
    }
def build_slightly_different_list_attacks_response(attack_id: str, test_id: str, flagged_events: int = 0, total_events: int = 0):
    return {
        "items": [
            {
                "attack": {
                    "id": attack_id,
                    "started_at": "2025-03-1215:34:00.50527",
                    "status": 2,
                    "dataset_name": "str",
                    "attack_name": "attack_name",
                    "risk": 0.0,
                    "runtime_seconds": 3.0,
                    "total_events": flagged_events,
                    "flagged_events": total_events,
                },
                "result": None
            }
        ],
        "test": build_slightly_different_test_response(test_id)
    }


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

    test_id = "test_id"
    attack_id = "example_id"

    requests_mock.get(
        f"{API_BASE}/tests/{test_id}/attacks",
        json=build_slightly_different_list_attacks_response(test_id=test_id, attack_id=attack_id),
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory(model_name="mistral")
    submit_sandbox_output = model_test_output_factory(risk_threshold=100)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=True)
    res = convert_test_to_cli_response(test=cli_response, malicious_sample_ratio=100)

    assert res.code() == 0
    captured = capsys.readouterr()
    stdout = captured.out
    snapshot.assert_match(stdout, 'stdout.json')


def test_text_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot, requests_mock: requests_mock.Mocker) -> None:
    auth.load_access_token = MagicMock(return_value="atoken")

    test_id = "test_id"

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": test_id,
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/tests/{test_id}/attacks",
        json=build_slightly_different_list_attacks_response(test_id),
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory(model_name="mistral")
    submit_sandbox_output = model_test_output_factory(risk_threshold=100)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=False)
    res = convert_test_to_cli_response(test=cli_response, malicious_sample_ratio=100)

    assert res.code() == 0
    captured = capsys.readouterr()
    stdout = captured.out

    assert "Attack attack_name done success" in stdout
    assert "attack_name" in stdout
    assert "success" in stdout
    assert "✅" in stdout
    assert "0 / 0" in stdout
    assert "Flagged Events" in stdout
    assert "Results - https://sandbox.mindgard.ai/r/test/test_id" in stdout


@pytest.mark.parametrize("flagged_events,total_events,risk_threshold,exit_code",
                         [(0, 10, 0.5, 0), (8, 10, 0.5, 1), (5, 10, 0.5, 1), (0, 0, 0.5, 0)])
def test_risk_threshold(flagged_events: int, total_events: int, risk_threshold: float, exit_code: int, requests_mock: requests_mock.Mocker) -> None:
    auth.load_access_token = MagicMock(return_value="atoken")

    test_id = "test_id"

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": test_id,
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/tests/{test_id}/attacks",
        json=build_slightly_different_list_attacks_response(test_id=test_id, flagged_events=flagged_events, total_events=total_events),
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory(model_name="mistral")
    submit_sandbox_output = model_test_output_factory(risk_threshold=risk_threshold)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=False)
    res = convert_test_to_cli_response(test=cli_response, malicious_sample_ratio=risk_threshold)

    assert res.code() == exit_code