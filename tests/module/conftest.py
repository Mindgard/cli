import os
from typing import TypedDict

from pytest import Config

from .utils import suppress_output

from ...src.mindgard.config import get_token_file
from ...src.mindgard.auth import load_access_token
from ...src.mindgard.orchestrator import get_tests

class ExampleIds(TypedDict):
    test_id: str
    attack_id: str

example_ids: ExampleIds



def pytest_configure(config: Config) -> None:
    # Check that the user has a valid token in their config directory
    token_file = get_token_file()
    assert os.path.exists(token_file)
    try:
        with suppress_output():
            access_token = load_access_token()
            tests = get_tests(str(access_token))

        test_id = tests[0].id
        attack_id = tests[0].attacks[0].id
        global example_ids
        example_ids = {"test_id": test_id, "attack_id": attack_id}

    except Exception as e:
        assert False, f"User that you are authenticated with should have previously run a test. This is required for tests to pass. Error: {e}"


def pytest_unconfigure() -> None:
    pass
