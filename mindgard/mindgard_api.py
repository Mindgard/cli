from dataclasses import dataclass
import logging
from typing import Any, Dict, Literal, Optional

import requests

from mindgard.constants import ATTACK_STATE_COMPLETED, ATTACK_STATE_RUNNING, VERSION, ATTACK_STATE_QUEUED

class GeneralException(Exception):
    """
    General exception when interacting with the Mindgard API.
    """

class HttpStatusException(Exception):
    """
    General exception when interacting with the Mindgard API.
    """

@dataclass
class AttackResponse():
    id: str
    name: str
    state: Literal["queued", "running", "completed"]
    errored: Optional[bool] = None
    risk: Optional[int] = None

@dataclass
class FetchTestDataResponse():
    has_finished: bool
    risk: int
    attacks: list[AttackResponse]


def api_response_to_attack_state(attack:Dict[str, Any]) -> AttackResponse:
    if attack["state"] == ATTACK_STATE_QUEUED:
        state = "queued"
    elif attack["state"] == ATTACK_STATE_RUNNING:
        state = "running"
    else:
        state = "completed"

    if attack["state"] < ATTACK_STATE_QUEUED:
        errored = True
    elif attack["state"] == ATTACK_STATE_COMPLETED:
        errored = False
    else:
        errored = None

    risk = attack.get("risk") if attack["state"] == ATTACK_STATE_COMPLETED else None
    return AttackResponse(
        id=attack["id"],
        name=attack["attack"],
        state=state,
        errored=errored,
        risk=risk,
    )

@dataclass
class FetchTestAttacksData():
    has_finished: bool

class MindgardApi():
    def fetch_test_data(
            self, 
            api_base:str, 
            access_token:str, 
            additional_headers:Optional[dict[str, str]],
            test_id:str
    ) -> Optional[FetchTestDataResponse]:
        response = requests.get(
            url=f"{api_base}/assessments/{test_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": f"mindgard-cli/{VERSION}",
                "X-User-Agent": f"mindgard-cli/{VERSION}",
                **(additional_headers or {})
            }
        )

        if response.status_code != 200:
            return None
        
        try:
            data = response.json()
        except requests.JSONDecodeError as jde:
            logging.error(f"Error decoding response: {jde}")
            return None

        try:
            attacks = [api_response_to_attack_state(attack) for attack in data["attacks"]]

            return FetchTestDataResponse(
                has_finished=data["hasFinished"],
                attacks=attacks,
                risk=data["risk"],
            )
        except KeyError as ke:
            logging.error(f"KeyError response: {ke}")
            return None
        
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