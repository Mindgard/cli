

from dataclasses import dataclass
import sys
from unittest import mock

import pytest
from mindgard.__main__ import main
from mindgard.orchestrator import OrchestratorSetupRequest, OrchestratorTestResponse

@dataclass
class Case:
    name: str
    input_args: list[str]
    expected_request: OrchestratorSetupRequest
    cli_run_response: OrchestratorTestResponse
    expected_exit_code: int

cases = [
    Case(
        name="basic",
        input_args=[
            'mindgard', 'test', 'mytarget', 
            '--system-prompt', 'mysysprompt', 
            '--preset', 'tester',
            '--parallelism', '4',
        ],
        expected_request=OrchestratorSetupRequest(
            target="mytarget",
            modelType="llm",
            system_prompt="mysysprompt",
            attackPack=None,
            attackSource="user",
            parallelism=4,
            labels=None
        ),
        cli_run_response=OrchestratorTestResponse(
            id="123",
            mindgardModelName="model",
            source="user",
            createdAt="2022-01-01",
            attacks=[],
            isCompleted=True,
            hasFinished=True,
            risk=12,
            test_url="http://example.com"
        ),
        expected_exit_code=0,
    ),
]


@pytest.mark.parametrize("test_case", cases, ids=lambda x: x.name)
@mock.patch("mindgard.__main__.exit")
@mock.patch("mindgard.__main__.cli_run")
@mock.patch("mindgard.__main__.model_test_submit_factory")
def test_orchestrator_setup_request(
    mock_model_test_submit_factory:mock.MagicMock, 
    mock_cli_run: mock.MagicMock, 
    mock_exit: mock.MagicMock,
    test_case: Case
):
    """
    Given a set of input arguments and a final response, validate that:
     - The OrchestratorSetupRequest is correctly constructed
     - Exit code is as expected
    """
    with mock.patch.object(sys, 'argv', test_case.input_args):
        mock_cli_run.return_value = test_case.cli_run_response
        
        main()
        
        mock_model_test_submit_factory.assert_called_once_with(
            request=test_case.expected_request,
            model_wrapper=mock.ANY,
            message_handler=mock.ANY,
        )
        mock_cli_run.assert_called_once_with(mock_model_test_submit_factory.return_value, mock.ANY, output_func=mock.ANY, json_out=mock.ANY)
        mock_exit.assert_called_once_with(test_case.expected_exit_code)
