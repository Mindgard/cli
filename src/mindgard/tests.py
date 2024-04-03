

import json
import sys
import time
from typing import Any, Dict, List, Optional

from requests import Response
import requests
from tabulate import tabulate

from .constants import VERSION

from .utils import api_get, api_post

from .auth import require_auth


# TODO: tidy this
def display_test_results(data: List[Dict[str, Any]]) -> None: # TODO: consider color-coded output for risks
    display_data: List[Dict[str, Any]] = []
    for d in data:
        row = {k: v for k, v in d.items() if k not in ["attacks", "updatedAt", "displayName", "source", "isCompleted", "hasFinished"]}
        row["attack_id"] = d["attacks"][0]["id"]
        row["attack_name"] = d["attacks"][0]["attack"]
        row["state"] = d["attacks"][0]["state_message"]
        row["runtime"] = d["attacks"][0]["runtime"] or time.time() - d["attacks"][0]["run_at_unix"]
        row["attack_risk"] = d["attacks"][0]["risk"] if d["attacks"][0]["state_message"] == "Completed" else "TBD"

        display_data.append(row)
        for attack in d["attacks"][1:]:
            display_data.append({
                "attack_id": attack["id"],
                "attack_name": attack["attack"],
                "state": attack["state_message"],
                "runtime": attack["runtime"] or time.time() - attack["run_at_unix"],
                "attack_risk": attack["risk"] if attack["state_message"] == "Completed" else "TBD",
            })
    print(tabulate(display_data, headers="keys"))


@require_auth
def get_tests(access_token: str, json_format: bool = False, test_id: Optional[str] = None) -> Response:
    url = f"https://api.sandbox.mindgard.ai/api/v1/assessments/{test_id}" if test_id else "https://api.sandbox.mindgard.ai/api/v1/assessments?ungrouped=true"
    res = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    })
    res.raise_for_status()
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()]
    if json_format:
        print(json.dumps(res.json()))
    else:
        display_test_results(data)
    return res


@require_auth
def run_test(access_token: str, attack_name: str, json_format: bool = False) -> Response:
    if not json_format:
        print("Initiating testing...")
    res = api_post("https://api.sandbox.mindgard.ai/api/v1/assessments", access_token, {"mindgardModelName": attack_name})
    if json_format:
        print(json.dumps(res.json())) # TODO: include url
    else:
        print("Test initiated. Waiting for results...")
        test_id = res.json()["id"]
        completed = False

        test_res = api_get(f"https://api.sandbox.mindgard.ai/api/v1/assessments/{test_id}", access_token)  
        completed = test_res.json()["hasFinished"]
        display_test_results([test_res.json()])

        num_lines = len(test_res.json()["attacks"]) + 2

        while not completed:
            time.sleep(1)

            sys.stdout.write(f"\033[{num_lines}A") 
            sys.stdout.write("\033[J")

            test_res = api_get(f"https://api.sandbox.mindgard.ai/api/v1/assessments/{test_id}", access_token)  
            completed = test_res.json()["hasFinished"]
            display_test_results([test_res.json()])
        print("Test completed.")
    return res
