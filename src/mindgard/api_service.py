import json
import os
from typing import List, Dict, Any
from .utils import api_get, api_post
from .constants import API_BASE

class ApiService():
    def get_tests(self, access_token: str) ->  List[Dict[str, Any]]:
        url = f"{API_BASE}/assessments?ungrouped=true"

        res = api_get(url, access_token)
        
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
        res = api_get(url, access_token)
        data: Dict[str, Any] = res.json()

        data["url"] = f"https://sandbox.mindgard.ai/r/test/{test_id}"
        for attack in data["attacks"]:
            attack_id = attack["id"]
            attack["url"] = f"https://sandbox.mindgard.ai/r/attack/{attack_id}"

        return data

    def submit_test(self, access_token: str, target_name:str) -> Dict[str, Any]:
        url = f"{API_BASE}/assessments"
        post_body = {"mindgardModelName": target_name}
        res = api_post(url, access_token, json=post_body)
        data: Dict[str, Any] = res.json()
        return data
    
    def get_orchestrator_websocket_connection_string(self, access_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_BASE}/tests/cli_init"

        # Extra configuration only currently available to Mindgardians
        extra_config = os.environ.get('MINDGARD_EXTRA_CONFIG', None)
        if extra_config:
            payload["extraConfig"] = json.loads(extra_config)
        pack = os.environ.get('ATTACK_PACK', "sandbox")
        payload["attackPack"] = pack
        # End of Mindgard-only configuration

        res = api_post(url, access_token, json=payload)
        data: Dict[str, Any] = res.json()
        return data