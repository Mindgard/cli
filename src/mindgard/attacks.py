


import json
from typing import Any, Dict, List, Optional
from requests import HTTPError
from tabulate import tabulate

from .utils import api_get,CliResponse, print_to_stderr
from .auth import require_auth


def display_attacks_results(data: List[Dict[str, Any]]) -> None:
    display_data: List[Dict[str, Any]] = []
    for d in data:
        row = {k: v for k, v in d.items() if k not in ["stacktrace", "submitted_at_unix", "run_at_unix"]}
        display_data.append(row)
    print(tabulate(display_data, headers="keys"))

@require_auth
def get_attacks(access_token: str, json_format: bool = False, attack_id: Optional[str] = None) -> CliResponse:
    url = f"https://api.sandbox.mindgard.ai/api/v1/results/{attack_id}" if attack_id else "https://api.sandbox.mindgard.ai/api/v1/users/experiments"
    try:
        res = api_get(url, access_token)
    except HTTPError as e:
        if "Bad Request" in str(e):
            error_message_addon = "Check the id you provided." if attack_id else "Contact Mindgard support."
            print_to_stderr("Bad Request when getting attack. " + error_message_addon)
            return CliResponse(2)
        else:
            raise e
        
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()] # TODO - res.json has different strucutre in sinlge vs multi
    # TODO: URGENT: single resource shoudl return id at the top level

    for item in data:
        if "id" in item:
            url_id = item["id"] 
        else:
            url_id = item["meta"]["id"]
        item["url"] = f"https://sandbox.mindgard.ai/r/attack/{url_id}"

    if json_format:
        print(json.dumps(data))
    else:
        print(json.dumps(data, indent=2)) if attack_id else display_attacks_results(data)
    return CliResponse(0)