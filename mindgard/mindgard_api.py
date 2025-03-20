from dataclasses import dataclass
from typing import Optional

import requests

from mindgard.constants import VERSION

class GeneralException(Exception):
    """
    General exception when interacting with the Mindgard API.
    """

class HttpStatusException(Exception):
    """
    General exception when interacting with the Mindgard API.
    """
    
@dataclass
class FetchTestAttacksData():
    has_finished: bool

class MindgardApi():
        
    def fetch_test_attacks(
        self, 
        api_base:str, 
        test_id:str,
        access_token:str,
        additional_headers:Optional[dict[str, str]],
    ) -> FetchTestAttacksData:

        try:
            response = requests.get(
                url=f"{api_base}/tests/{test_id}/attacks",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": f"mindgard-cli/{VERSION}",
                    "X-User-Agent": f"mindgard-cli/{VERSION}",
                    **(additional_headers or {}),
                },
            )
        except requests.RequestException as e:
            raise GeneralException(f"error calling api: {e.__class__.__name__}") from e
        except Exception as e:
            raise GeneralException(f"error calling api: unknown exception") from e

        if response.status_code != 200:
            raise HttpStatusException(f"error calling api. expected 200, got: {response.status_code}")

        try:
            data = response.json()
        except requests.JSONDecodeError as e:
            raise GeneralException(f"error decoding api response: {e}") from e
        
        try:
            return FetchTestAttacksData(
                has_finished=data["test"]["has_finished"],
            )
        except TypeError as e:
            raise GeneralException(f"error parsing api response: {e}") from e