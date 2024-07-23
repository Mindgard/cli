
from typing import List, Tuple
import pytest

from argparse import Namespace
from src.mindgard.__main__ import parse_args


argparse_success_test_cases: List[Tuple[str, Namespace]] = [
    # normal user login
    ("login", Namespace(command='login', log_level='warn', instance=None)),

    # login to an instance
    ("login --instance deployed_instance", Namespace(command='login', log_level='warn', instance='deployed_instance')),

    # when no --instance parameter is passed it should default to sandbox
    ("login --instance", Namespace(command='login', log_level='warn', instance=None)),  # missing instance value
    # new cli structure:
    ("sandbox cfp_faces", Namespace(command='sandbox', target='cfp_faces', json=False, risk_threshold=80, log_level='warn')),

    ("list tests", Namespace(command='list', list_command='tests', json=False, id=None, log_level='warn')),
    ("list tests --json", Namespace(command='list', list_command='tests', json=True, id=None, log_level='warn')),
    ("list tests --json --id 123", Namespace(command='list', list_command='tests', json=True, id='123', log_level='warn')),
]

argparse_failure_test_cases: List[str] = [
    ("attackcategories --json --id 123"),
    ("auth --json"),
    ("tests run --name cfp_faces --json --id 123"),
    ("attacks --json --id 123 --name cfp_faces"),
    ("attacks --json --id 123 --name cfp_faces --json"),
]


# pytest test for each argparse_test_case

@pytest.mark.parametrize("test_case", argparse_success_test_cases, ids=lambda x: x[0])
def test_argparse_expected_namespaces(test_case: Tuple[str, Namespace]) -> None:
    command, namespace = test_case
    print(f"command: {command.split()}, namespace: {namespace}")
    parsed_args = parse_args(command.split())
    assert parsed_args == namespace
    
@pytest.mark.parametrize("test_case", argparse_failure_test_cases, ids=lambda x: x)
def test_argparse_expected_failures(test_case: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(test_case.split())