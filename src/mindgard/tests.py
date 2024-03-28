

import json
from typing import Any, Dict, List, Optional

import requests
from tabulate import tabulate

from .constants import VERSION
from .auth import require_auth


@require_auth
def get_tests(access_token: str, json_format: bool = False, test_id: Optional[str] = None) -> requests.Response:
    url = f"https://api.sandbox.mindgard.ai/api/v1/assessments/{test_id}" if test_id else "https://api.sandbox.mindgard.ai/api/v1/assessments?ungrouped=true"
    res = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    })
    res.raise_for_status()     
    data: List[Dict[str, Any]] = res.json()[0] if isinstance(res.json(), list) else [res.json()]
    if json_format:
        print(json.dumps(res.json()))
    else:
        display_data: List[Dict[str, Any]] = []
        for d in data:
            row = {k: v for k, v in d.items() if k != "attacks"}
            row["attack_ids"] = d["attacks"][0]["id"]
            display_data.append(row)
            for attack in d["attacks"][1:]:
                display_data.append({"attack_ids": attack["id"]})
        print(tabulate(display_data, headers="keys"))
    return res


@require_auth
def run_test(access_token: str, attack_name: str, json_format: bool = False) -> requests.Response:
    url = "https://api.sandbox.mindgard.ai/api/v1/assessments" 
    res = requests.post(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    }, json={"mindgardModelName": attack_name})
    res.raise_for_status()
    if json_format:
        print(json.dumps(res.json()))
    else:
        # TODO: lots of things
        print(res.json())
    return res
