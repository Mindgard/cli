


import json
from typing import Any, Dict, List, Optional
from requests import Response
from tabulate import tabulate

from .utils import api_get
from .auth import require_auth


@require_auth
def attackcategories(access_token: str, json_format: bool = False) -> Response:
    res = api_get("https://api.sandbox.mindgard.ai/api/v1/attacks/categories", access_token)
    category_names: List[str] = list(map(lambda x: x["category"], res.json()))
    print(json.dumps(res.json(), indent=2)) if json_format else print("\n".join(category_names))
    return res


def display_attacks_results(data: List[Dict[str, Any]]) -> None:
    display_data: List[Dict[str, Any]] = []
    for d in data:
        row = {k: v for k, v in d.items() if k not in ["stacktrace", "submitted_at_unix", "run_at_unix"]}

        display_data.append(row)
    print(tabulate(display_data, headers="keys"))


@require_auth
def get_attacks(access_token: str, json_format: bool = False, attack_id: Optional[str] = None) -> Response:
    url = f"https://api.sandbox.mindgard.ai/api/v1/results/{attack_id}" if attack_id else "https://api.sandbox.mindgard.ai/api/v1/users/experiments"
    res = api_get(url, access_token)
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()]
    if json_format:
        print(json.dumps(res.json()))
    else:
        print(json.dumps(res.json(), indent=2)) if attack_id else display_attacks_results(data)
    return res
