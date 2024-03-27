import os

from ...src.mindgard.__main__ import attackcategories
from ...src.mindgard.auth import get_token_file


def pytest_configure() -> None:
    # Check that the user has a valid token in their config directory
    token_file = get_token_file()
    assert os.path.exists(token_file)
    try:
        res_json = attackcategories()
        assert res_json is not None
        res_json.raise_for_status()
    except Exception as e:
        assert False, f"Failed when checking saved auth token: {e}. Check that you are authenticated, and that orchestrator is running."
    

def pytest_unconfigure() -> None:
    pass
