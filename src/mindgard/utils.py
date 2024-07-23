from argparse import Namespace
import os
import sys
from typing import Any, Dict, Optional, Tuple
import json

import toml
import requests

from .constants import (
    REPOSITORY_URL,
    VERSION,
    API_RETRY_ATTEMPTS,
    API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS,
)

from tenacity import retry, stop_after_attempt, wait_fixed


from .orchestrator import OrchestratorTestResponse

class CliResponse:
    def __init__(self, code: int):
        self._code = code

    def code(self) -> int:
        return self._code


def test_to_cli_response(test: OrchestratorTestResponse, risk_threshold: int) -> CliResponse:
    if test.risk > risk_threshold:
        return CliResponse(1)
    else:
        return CliResponse(0)


def print_to_stderr(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def print_to_stderr_as_json(dict: Any) -> None:
    print(json.dumps(dict), file=sys.stderr)


def version_to_tuple(version: str) -> Tuple[int, ...]:
    return tuple(map(int, version.split(".")))


def is_version_outdated() -> Optional[str]:
    try:
        res = requests.get(REPOSITORY_URL)
        res.raise_for_status()
        latest_version = res.json()["info"]["version"]
        latest_version_tuple = version_to_tuple(latest_version)
        current_version_tuple = version_to_tuple(VERSION)
        return latest_version if latest_version_tuple > current_version_tuple else None
    except Exception:
        return ""


def parse_toml_and_args_into_final_args(
    config_file_path: Optional[str], args: Namespace
) -> Dict[str, Any]:
    config_file = config_file_path or "mindgard.toml"
    toml_args = {}
    try:
        with open(config_file, "r") as f:
            contents = f.read()
            toml_args = toml.loads(contents)
    except FileNotFoundError:
        if config_file_path is None:
            pass
        else:
            raise ValueError(
                f"Config file not found: {config_file=}. Check that the file exists on disk."
            )

    final_args = {
        k: v or toml_args.get(k) or toml_args.get(k.replace("_", "-"))
        for k, v in vars(args).items()
    }

    final_args["api_key"] = final_args["api_key"] or os.environ.get(
        "MODEL_API_KEY", None
    )

    return final_args
