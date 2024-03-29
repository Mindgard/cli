


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


@require_auth
def get_attacks(access_token: str, json_format: bool = False, attack_id: Optional[str] = None) -> Response:
    url = f"https://api.sandbox.mindgard.ai/api/v1/results/{attack_id}" if attack_id else "https://api.sandbox.mindgard.ai/api/v1/users/experiments"
    res = api_get(url, access_token)
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()]
    if json_format:
        print(json.dumps(res.json()))
    else:
        print(tabulate(data, headers="keys"))
    return res
