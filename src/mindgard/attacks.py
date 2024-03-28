


import json
from typing import Any, Dict, List, Optional
import requests
from tabulate import tabulate

from .constants import VERSION
from .auth import require_auth


@require_auth
def attackcategories(access_token: str, json_format: bool = False) -> requests.Response:
    res = requests.get("https://api.sandbox.mindgard.ai/api/v1/attacks/categories", headers={
        "Authorization": f"Bearer {access_token}", 
        "User-Agent": f"mindgard/{VERSION}"
    })
    res.raise_for_status()
    category_names: List[str] = list(map(lambda x: x["category"], res.json()))
    print(json.dumps(res.json(), indent=2)) if json_format else print("\n".join(category_names))
    return res


@require_auth
def get_attacks(access_token: str, json_format: bool = False, attack_id: Optional[str] = None) -> requests.Response:
    url = f"https://api.sandbox.mindgard.ai/api/v1/results/{attack_id}" if attack_id else "https://api.sandbox.mindgard.ai/api/v1/users/experiments"
    res = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    })
    res.raise_for_status()
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()]
    if json_format:
        print(json.dumps(res.json()))
    else:
        print(tabulate(data, headers="keys"))
    return res
