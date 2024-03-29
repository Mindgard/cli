import sys
from typing import Any, Dict, Optional, Tuple

import requests

from .constants import REPOSITORY_URL, VERSION


def print_to_stderr(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


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
        return ''
    

def api_get(url: str, access_token: str) -> requests.Response:
    res = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    })
    res.raise_for_status()
    return res


def api_post(url: str, access_token: str, json: Dict[str, Any]) -> requests.Response:
    res = requests.post(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    }, json=json)
    res.raise_for_status()
    return res

