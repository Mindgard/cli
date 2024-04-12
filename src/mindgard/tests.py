import time
from typing import Any, Dict, List, Optional

import requests
from tabulate import tabulate

from .constants import VERSION

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


def api_get_tests(access_token: str, test_id: Optional[str] = None) -> List[Dict[str, Any]]:
    url = f"https://api.sandbox.mindgard.ai/api/v1/assessments/{test_id}" if test_id else "https://api.sandbox.mindgard.ai/api/v1/assessments?ungrouped=true"
    res = requests.get(url, headers={
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard/{VERSION}"
    })
    res.raise_for_status()
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()]

    for item in data:
        test_id = item["id"]
        item["url"] = f"https://sandbox.mindgard.ai/r/test/{test_id}"

    return data