from dataclasses import dataclass
import logging
from typing import Any, Dict, Literal, Optional

import requests

from mindgard.constants import VERSION


@dataclass
class AttackResponse():
    id: str
    name: str
    state: Literal["queued", "running", "completed"]
    errored: Optional[bool]
    risk: Optional[int]

@dataclass
class FetchTestDataResponse():
    has_finished: bool
    attacks: list[AttackResponse]


def api_response_to_attack_state(attack:Dict[str, Any]) -> AttackResponse:
    if attack["state"] == 0:
        state = "queued"
    elif attack["state"] == 1:
        state = "running"
    else:
        state = "completed"

    if attack["state"] < 0:
        errored = True
    elif attack["state"] == 2:
        errored = False
    else:
        errored = None

    risk = attack.get("risk") if attack["state"] == 2 else None
    return AttackResponse(
        id=attack["id"],
        name=attack["attack"],
        state=state,
        errored=errored,
        risk=risk,
    )

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
                attacks=attacks
            )
        except KeyError as ke:
            logging.error(f"KeyError response: {ke}")
            return None
        
