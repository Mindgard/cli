from typing import List, Dict, Any
import requests
from .constants import VERSION, API_BASE

class ApiService():
    def get_tests(self, access_token: str) ->  List[Dict[str, Any]]:
        url = f"{API_BASE}/assessments?ungrouped=true"

        res = requests.get(url, headers={
            "Authorization": f"Bearer {access_token}",
            "X-User-Agent": f"mindgard-cli/{VERSION}"
        })
        
        res.raise_for_status()
        
        data: List[Dict[str, Any]] = res.json()

        # augment the output with the shortened url
        for test in data:
            test_id = test["id"]
            test["url"] = f"https://sandbox.mindgard.ai/r/test/{test_id}"
            for attack in test["attacks"]:
                attack_id = attack["id"]
                attack["url"] = f"https://sandbox.mindgard.ai/r/attack/{attack_id}"

        return data

    def get_test(self, access_token: str, test_id:str) -> Dict[str, Any]:
        url = f"{API_BASE}/assessments/{test_id}"

        res = requests.get(url, headers={
            "Authorization": f"Bearer {access_token}",
            "X-User-Agent": f"mindgard-cli/{VERSION}"
        })
        
        res.raise_for_status()
        
        data: Dict[str, Any] = res.json()

        data["url"] = f"https://sandbox.mindgard.ai/r/test/{test_id}"
        for attack in data["attacks"]:
            attack_id = attack["id"]
            attack["url"] = f"https://sandbox.mindgard.ai/r/attack/{attack_id}"

        return data

    def submit_test(self, access_token: str, target_name:str) -> Dict[str, Any]:
        url = f"{API_BASE}/assessments"
        post_body = {"mindgardModelName": target_name}
        res = requests.post(url, headers={
            "Authorization": f"Bearer {access_token}",
            "X-User-Agent": f"mindgard-cli/{VERSION}"
        }, json=post_body)
        res.raise_for_status()
        data: Dict[str, Any] = res.json()
        return data

    def fetch_llm_prompts(self, access_token: str) -> Dict[str, Any]:
        url = f"{API_BASE}/llm_tests/prompts"

        res = requests.get(url, headers={
            "Authorization": f"Bearer {access_token}",
            "X-User-Agent": f"mindgard-cli/{VERSION}"
        })
        
        res.raise_for_status()
        
        data: Dict[str, Any] = res.json()
        return data
    
    def submit_llm_responses(self, access_token: str, responses:Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_BASE}/llm_tests/responses"

        res = requests.post(url, headers={
            "Authorization": f"Bearer {access_token}",
            "X-User-Agent": f"mindgard-cli/{VERSION}"
        }, json=responses)
        
        res.raise_for_status()
        
        data: Dict[str, Any] = res.json()
        return data