from typing import Any, Dict, List, Optional
import requests
from .src.mindgard.constants import VERSION
from .src.mindgard.auth import require_auth


class SandboxApi:
    def __init__(self, access_token:str, base_url:Optional[str] = "https://api.sandbox.mindgard.ai/api/v1"):
        self.base_url = base_url
        self.access_token = access_token

    @require_auth
    def get_tests(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/assessments/?ungrouped=true"
        res = requests.get(url, headers={
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": f"mindgard/{VERSION}"
        })
        res.raise_for_status()
        return res
    
    @require_auth
    def get_test(self, id:str) -> Dict[str, Any]:
        url = f"{self.base_url}/assessments/{id}"
        res = requests.get(url, headers={
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": f"mindgard/{VERSION}"
        })
        res.raise_for_status()
        return res

    def get_test(self, id:str) -> Dict[str, Any]:
        pass