# Types
from typing import Callable, Dict, Any

# Requests
import requests

from .constants import (
    VERSION,
    API_RETRY_ATTEMPTS,
    API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS,
)

from tenacity import retry, stop_after_attempt, wait_fixed

# Type aliases
type_post_request_function = Callable[[str, str, Dict[str, Any]], requests.Response]
type_get_request_function = Callable[[str, str], requests.Response]


def _standard_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": f"mindgard-cli/{VERSION}",
        "X-User-Agent": f"mindgard-cli/{VERSION}",
    }


@retry(
    stop=stop_after_attempt(API_RETRY_ATTEMPTS),
    wait=wait_fixed(API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS),
    reraise=True,
)
def api_post(url: str, access_token: str, payload: Dict[str, Any]) -> requests.Response:
    response = requests.post(
        url=url, json=payload, headers=_standard_headers(access_token)
    )
    response.raise_for_status()
    return response


@retry(
    stop=stop_after_attempt(API_RETRY_ATTEMPTS),
    wait=wait_fixed(API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS),
    reraise=True,
)
def api_get(url: str, access_token: str) -> requests.Response:
    response = requests.get(url=url, headers=_standard_headers(access_token))
    response.raise_for_status()
    return response
