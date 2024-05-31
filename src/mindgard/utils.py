from argparse import Namespace
import sys
from typing import Any, Dict, Optional, Tuple

import toml
from .error import ExpectedError
import requests

from .constants import REPOSITORY_URL, VERSION

class CliResponse():
    def __init__(self, code:int):
        self._code = code

    def code(self) -> int:
        return self._code

def print_to_stderr(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def version_to_tuple(version: str) -> Tuple[int, ...]:
    return tuple(map(int, version.split(".")))


def api_get(url: str, access_token: str) -> requests.Response:
    res = requests.get(url, headers=standard_headers(access_token))
    res.raise_for_status()
    return res


def api_post(url: str, access_token: str, json: Dict[str, Any]) -> requests.Response:
    res = requests.post(url, headers=standard_headers(access_token), json=json)
    res.raise_for_status()
    return res
        

def is_version_outdated() -> Optional[str]:
    try:
        res = requests.get(REPOSITORY_URL)
        res.raise_for_status()
        latest_version = res.json()["info"]["version"]
        latest_version_tuple = version_to_tuple(latest_version)
        current_version_tuple = version_to_tuple(VERSION)
        return latest_version if latest_version_tuple > current_version_tuple else None
    except Exception:
        return ''
    

def standard_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard-cli/{VERSION}",
        "X-User-Agent": f"mindgard-cli/{VERSION}"
    }
    
def parse_toml_and_args_into_final_args(config_file_path: Optional[str], args: Namespace) -> Dict[str, Any]:
    config_file = config_file_path or "mindgard.toml"
    toml_args = {}
    try:
        with open(config_file, 'r') as f:
            contents = f.read()
            toml_args = toml.loads(contents)
    except FileNotFoundError:
        if config_file_path is None:
            pass
        else:
            raise ExpectedError(f"Config file not found: {config_file=}. Check that the file exists on disk.")

    final_args = {k: v or toml_args.get(k) or toml_args.get(k.replace("_", "-")) for k, v in vars(args).items()}

    return final_args