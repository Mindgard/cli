
from typing import List, Tuple
import pytest

from argparse import Namespace
from ...src.mindgard.__main__ import parse_args


argparse_success_test_cases: List[Tuple[str, Namespace]] = [
    ("login", Namespace(command='login')),
    ("attacks", Namespace(command='attacks', json=False, id=None)),
    ("attacks --id 123", Namespace(command='attacks', json=False, id='123')),
    ("attacks --json", Namespace(command='attacks', json=True, id=None)),
    ("attacks --json --id 123", Namespace(command='attacks', json=True, id='123')),
    # new cli structure:
    ("sandboxtest cfp_faces", Namespace(command='sandboxtest', target='cfp_faces', json=False, risk_threshold=80)),

    ("list tests", Namespace(command='list', list_command='tests', json=False, id=None)),
    ("list tests --json", Namespace(command='list', list_command='tests', json=True, id=None)),
    ("list tests --json --id 123", Namespace(command='list', list_command='tests', json=True, id='123')),
    #TODO singulars - the 'aliases' feature of argparse didn't work as expected and didn't want to block
    # ("list test", Namespace(command='list', list_command='tests', json=False, id=None)),
    # ("list test --json", Namespace(command='list', list_command='tests', json=True, id=None)),
    # ("list test --json --id 123", Namespace(command='tests', test_command=None, json=True, id='123')),
]

argparse_failure_test_cases: List[str] = [
    ("attackcategories --json --id 123"),
    ("auth --json"),
    ("tests run --name cfp_faces --json --id 123"),
    # ("tests --json run --name cfp_faces"), # It would be nice for this to fail, but not implemented yet
    # ("tests --json --id 123 run --name cfp_faces"), # It would be nice for this to fail, but not implemented yet
    ("attacks --json --id 123 --name cfp_faces"),
    ("attacks --json --id 123 --name cfp_faces --json"),
]


# pytest test for each argparse_test_case


@pytest.mark.parametrize("test_case", argparse_success_test_cases, ids=lambda x: x[0])
def test_argparse_expected_namespaces(test_case: Tuple[str, Namespace]) -> None:
    command, namespace = test_case
    parsed_args = parse_args(command.split())
    assert parsed_args == namespace
    

@pytest.mark.parametrize("test_case", argparse_failure_test_cases, ids=lambda x: x)
def test_argparse_expected_failures(test_case: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(test_case.split())