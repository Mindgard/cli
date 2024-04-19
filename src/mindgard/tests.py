import requests
from typing import Any, Dict, List, Optional

from .utils import standard_headers


def api_get_tests(access_token: str, test_id: Optional[str] = None) -> List[Dict[str, Any]]:
    url = f"https://api.sandbox.mindgard.ai/api/v1/assessments/{test_id}" if test_id else "https://api.sandbox.mindgard.ai/api/v1/assessments?ungrouped=true"
    res = requests.get(url, headers=standard_headers(access_token))
    res.raise_for_status()
    data: List[Dict[str, Any]] = res.json() if isinstance(res.json(), list) else [res.json()]

    for item in data:
        test_id = item["id"]
        item["url"] = f"https://sandbox.mindgard.ai/r/test/{test_id}"

    return data