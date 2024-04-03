
from typing import List, Tuple
import pytest

from argparse import Namespace
from ...src.mindgard.__main__ import parse_args


argparse_success_test_cases: List[Tuple[str, Namespace]] = [
    ("attackcategories", Namespace(command='attackcategories', json=False)),
    ("attackcategories --json", Namespace(command='attackcategories', json=True)),
    ("auth", Namespace(command='auth')),
    ("tests", Namespace(command='tests', test_commands=None, json=False, id=None)),
    ("tests --json", Namespace(command='tests', test_commands=None, json=True, id=None)),
    ("tests --id 123", Namespace(command='tests', test_commands=None, json=False, id='123')),
    ("tests --json --id 123", Namespace(command='tests', test_commands=None, json=True, id='123')),
    ("tests run --name cfp_faces", Namespace(command='tests', test_commands='run', name='cfp_faces', json=False, id=None)),
    ("tests run --name cfp_faces --json", Namespace(command='tests', test_commands='run', name='cfp_faces', json=True, id=None)),
    ("attacks", Namespace(command='attacks', json=False, id=None)),
    ("attacks --id 123", Namespace(command='attacks', json=False, id='123')),
    ("attacks --json", Namespace(command='attacks', json=True, id=None)),
    ("attacks --json --id 123", Namespace(command='attacks', json=True, id='123')),     
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