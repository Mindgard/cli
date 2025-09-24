import platform
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


def build_tests_attacks_response(test_id: str = "blah", attack_id: str = "blah", flagged_events: int = 0,
                                 total_events: int = 0, model_name: str = "my-test-target"):
    return {
        "test": {
            "id": test_id,
            "has_finished": True,
            "model_name": model_name,
            "total_events": total_events,
            "flagged_events": flagged_events,
        },
        "items": [
            {
                "attack": {
                    "id": attack_id,
                    "attack_name": "blah",
                    "status": 2,
                    "total_events": total_events,
                    "flagged_events": flagged_events,
                }
            }
        ]
    }

def test_json_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot, requests_mock: requests_mock.Mocker) -> None:
    # fixture = _helper_fixtures()

    auth.load_access_token = MagicMock(return_value="atoken")

    test_id: str = "a-test-id-for-this-test"

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": test_id,
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/tests/{test_id}/attacks",
        json=build_tests_attacks_response(test_id=test_id),
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory()
    submit_sandbox_output = model_test_output_factory(risk_threshold=100)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=True)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=100)

    assert res.code() == 0
    captured = capsys.readouterr()
    stdout = captured.out
    snapshot.assert_match(stdout, 'stdout.json')

def test_text_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot, requests_mock: requests_mock.Mocker) -> None:
    auth.load_access_token = MagicMock(return_value="atoken")

    test_id: str = "a-test-id-for-this-test"
    target_name = "my-test-target"

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": test_id,
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/tests/{test_id}/attacks",
        json=build_tests_attacks_response(test_id=test_id, model_name=target_name),
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory()
    submit_sandbox_output = model_test_output_factory(risk_threshold=100)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=False)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=100)

    assert res.code() == 0
    captured = capsys.readouterr()
    stdout = captured.out

    if platform.system() == "Windows":
        # TODO: this is a basic check as Rich renders differently on windows
        assert f"https://sandbox.mindgard.ai/results/targets/{target_name}/tests/{test_id}".replace("\n","") in stdout.replace("\n","")
        assert "Attack blah done success" in stdout
    else:
        snapshot.assert_match(stdout, 'stdout.txt')

@pytest.mark.parametrize("flagged_events,total_events,risk_threshold,exit_code",
                         [(0, 10, 0.5, 0), (8, 10, 0.5, 1), (5, 10, 0.5, 1), (0, 0, 0.5, 0)])
def test_risk_threshold(flagged_events: int, total_events: int, risk_threshold: float, exit_code: int, requests_mock: requests_mock.Mocker) -> None:
    auth.load_access_token = MagicMock(return_value="atoken")

    requests_mock.post(
        f"{API_BASE}/assessments",
        json={
            "id": "test_id",
        },
        status_code=200,
    )

    requests_mock.get(
        f"{API_BASE}/tests/test_id/attacks",
        json=build_tests_attacks_response(test_id="test_id", flagged_events=flagged_events, total_events=total_events,),
        status_code=200,
    )

    submit_sandbox_submit = submit_sandbox_submit_factory()
    submit_sandbox_output = model_test_output_factory(risk_threshold=risk_threshold)

    cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=False)
    res = convert_test_to_cli_response(test=cli_response, risk_threshold=risk_threshold)

    assert res.code() == exit_code