import os
from typing import TypedDict

from pytest import Config

from ...src.mindgard.__main__ import attackcategories, get_tests
from ...src.mindgard.auth import get_token_file


class ExampleIds(TypedDict):
    test_id: str
    attack_id: str

example_ids: ExampleIds


def pytest_configure(config: Config) -> None:
    # Check that the user has a valid token in their config directory
    token_file = get_token_file()
    assert os.path.exists(token_file)
    try:
        res_json = attackcategories()
        assert res_json is not None
        res_json.raise_for_status()
    except Exception as e:
        assert False, f"Failed when checking saved auth token: {e}. Check that you are authenticated, and that orchestrator is running."
    try:
        res_json = get_tests(json_format=True)
        assert res_json is not None
        res_json.raise_for_status()
        assert len(res_json.json()) > 0
        test_id = res_json.json()[0]['id']
        attack_id = res_json.json()[0]['attacks'][0]["id"]
        global example_ids
        example_ids = {"test_id": test_id, "attack_id": attack_id}

    except Exception as e:
        assert False, f"User that you are authenticated with should have previously run a test. This is required for tests to pass. Error: {e}"


def pytest_unconfigure() -> None:
    pass
