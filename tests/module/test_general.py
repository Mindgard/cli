
import json
from typing import Any, Callable, Dict, List, NotRequired, Optional, TypedDict

import pytest
import requests

from ...src.mindgard.__main__ import (attackcategories, get_attacks, get_tests,
                                      run_test)
from .conftest import example_ids


class CommandTestCase(TypedDict):
    command: Callable[..., Optional[requests.Response]]
    kwargs: Dict[str, Any]
    expected_stdout: Optional[List[str]]
    expected_error: Optional[List[str]]
    custom_test: NotRequired[bool]
    status_code: NotRequired[int]
    fails: NotRequired[bool]


# This is suitable for CLI routes that return a requests.Response object
# custom_test: True is used to indicate parameter inputs that are not suitable for this function and should be handled separately
test_cases: List[CommandTestCase] = [
    {
        "command": attackcategories,
        "kwargs": {"json_format": True},
        "expected_stdout": ['"evasion"'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": attackcategories,
        "kwargs": {"json_format": False},
        "expected_stdout": ["evasion"],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_attacks,
        "kwargs": {"json_format": True},
        "expected_stdout": ['"id":', '"model":', '"dataset":', '"attack":', '"url":'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_attacks,
        "kwargs": {"json_format": False},
        "expected_stdout": ["--------------------", "id", "model", "dataset", "attack"],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_attacks,
        "kwargs": {"json_format": True, "attack_id": example_ids["attack_id"]},
        "expected_stdout": ['"risk_text": [{'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_attacks,
        "kwargs": {"json_format": False, "attack_id": example_ids["attack_id"]},
        "expected_stdout": ['"id":', '"model":', '"dataset":', '"attack":'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_attacks,
        "kwargs": {"json_format": False, "attack_id": "thisisinvalid"},
        "expected_stdout": None,
        "expected_error": ['Bad Request'],
        "expected_response_code": 1,
    },
    {
        "command": get_tests,
        "kwargs": {"json_format": False},
        "expected_stdout": ["------------------------", "attack_id", "Completed"],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_tests,
        "kwargs": {"json_format": True},
        "expected_stdout": ['[{"id": "', '"hasFinished": true', '"url":'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_tests,
        "kwargs": {"json_format": True, "test_id": example_ids["test_id"]},
        "expected_stdout": ['{"id": "', '"hasFinished": true'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_tests,
        "kwargs": {"json_format": False, "test_id": example_ids["test_id"]},
        "expected_stdout": ["------------------------", "attack_id", "Completed"],        
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": get_tests,
        "kwargs": {"json_format": False, "test_id": "thisisinvalid"},
        "expected_stdout": None,
        "expected_error": ['Bad Request'],
        "expected_response_code": 1,
    },
    {
        "command": run_test,
        "kwargs": {"attack_name": "cfp_faces", "json_format": True, "risk_threshold":100},
        "expected_stdout": ['{"id": "'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {
        "command": run_test,
        "kwargs": {"attack_name": "cfp_faces", "json_format": False, "risk_threshold":0},
        "expected_stdout": ['above threshold of'],
        "expected_error": None,
        "expected_response_code": 2,
    },
    {
        "command": run_test,
        "kwargs": {"attack_name": "cfp_faces", "json_format": False, "risk_threshold":101},
        "expected_stdout": ['under threshold of'],
        "expected_error": None,
        "expected_response_code": 0,
    },
    {   
        "custom_test": True,
        "command": run_test,
        "kwargs": {"attack_name": "cfp_faces", "json_format": False, "risk_threshold":100},
        "expected_stdout": ['below threshold of'],
        "expected_error": None,
        "expected_response_code": 2, # risk threshold
    }
]

def kwargs_to_named_args_str(kwargs: Dict[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in kwargs.items())

def create_custom_name(test_case: CommandTestCase) -> str:
    fn_name = test_case["command"].__name__
    keyword_args_str = kwargs_to_named_args_str(test_case["kwargs"])
    return f"{fn_name}({keyword_args_str})"

non_custom_test_cases = list(filter(lambda x: not x.get("custom_test"), test_cases))


def check_stderr(test_case: CommandTestCase, err: str) -> None:
    if test_case["expected_error"]:
        for line in test_case["expected_error"]:
            assert line in err
    else:
        assert not err

def check_stdout(test_case: CommandTestCase, out: str) -> None:
    if test_case["expected_stdout"]:
        for line in test_case["expected_stdout"]:
            assert line in out
    else:
        assert not out


@pytest.mark.parametrize("test_case", non_custom_test_cases, ids=lambda x: create_custom_name(x))
def test_cli_routes(test_case: CommandTestCase, capfd: pytest.CaptureFixture[str]) -> None:
    
    res = test_case["command"](**test_case["kwargs"])

    assert res.code() == test_case["expected_response_code"]

    # Check stdout and stderr
    out, err = capfd.readouterr()
    check_stdout(test_case, out)
    check_stderr(test_case, err)

    # Check jsonic
    if test_case["kwargs"]["json_format"]:
        try:
            json.loads(out) 
        except json.JSONDecodeError:
            assert False, "Output is not a valid JSON"


    if not test_case["expected_stdout"] and not test_case["expected_error"]:
        raise ValueError("At least one of expected_stdout or expected_error must be provided")
