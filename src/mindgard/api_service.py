from typing import List, Dict, Any
import requests
from .constants import VERSION, API_BASE

class ApiService():
    def get_tests(self, access_token: str) ->  List[Dict[str, Any]]:
        url = f"{API_BASE}/assessments?ungrouped=true"

        res = requests.get(url, headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": f"mindgard/{VERSION}"
        })
        
        res.raise_for_status()
        
        data: List[Dict[str, Any]] = res.json()

        # augment the output with the shortened url
        for test in data:
            test_id = test["id"]
            test["url"] = f"https://sandbox.mindgard.ai/r/tests/{test_id}"
            for attack in test["attacks"]:
                attack_id = attack["id"]
                attack["url"] = f"https://sandbox.mindgard.ai/r/attack/{attack_id}"


        return data