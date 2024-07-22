# Types
from pydantic import BaseModel, model_validator
from typing import Optional, Any, Dict, Literal, cast, List

from .constants import API_BASE, DASHBOARD_URL
from .api_service import type_post_request_function, type_get_request_function, api_get

import os
import json
from requests.exceptions import HTTPError

# Tells pydantic to stop worrying about model_type namespace collision
BaseModel.model_config["protected_namespaces"] = ()


# Type definitions
type_attack_pack = Literal["sandbox", "threat_intel"]


class OrchestratorSetupRequest(BaseModel):
    user: str
    userAgent: str
    targetModelName: str
    url: str
    model_type: str
    system_prompt: Optional[str] = None
    dataset: Optional[str] = None
    attackPack: type_attack_pack
    extraConfig: Optional[Dict[str, Any]]
    attackSource: str
    parallelism: int

    @model_validator(mode="after")  # type: ignore
    def check_system_prompt_or_dataset(self):
        if (
            self.system_prompt
            and self.dataset
            or not self.system_prompt
            and not self.dataset
        ):
            raise ValueError(
                "Only one of system prompt or dataset can be provided, not both."
            )

        if self.parallelism < 1:
            raise ValueError("Parallelism must be greater than 0.")

        return self


class OrchestratorSetupResponse(BaseModel):
    url: str
    group_id: str


class AttackModel(BaseModel):
    id: str
    submitted_at: str
    submitted_at_unix: float
    run_at: str
    run_at_unix: float
    state: Literal[0, 1, 2, -1]
    state_message: Literal["Completed", "Queued", "Running", "Failed"]
    runtime: float
    model: str
    dataset: str
    attack: str
    risk: int
    stacktrace: Optional[str]


class OrchestratorTestResponse(BaseModel):
    id: str
    mindgardModelName: str
    source: Literal["threat_intel", "user"]
    createdAt: str
    attacks: List[AttackModel]
    isCompleted: bool
    hasFinished: bool
    risk: int
    test_url: str


# class OrchestratorAttackResponse(BaseModel):
#     attack: str
#     id: int
#     is_finished: bool


def get_tests(
    access_token: str, request_function: type_get_request_function
) -> List[OrchestratorTestResponse]:
    url = f"{API_BASE}/assessments?ungrouped=true"

    try:
        response = request_function(url, access_token)

        return [
            OrchestratorTestResponse(
                **data, test_url=f"{API_BASE}/assessments/{data['id']}"
            )
            for data in response.json()
        ]
    except Exception as e:
        raise e


def get_test_by_id(
    test_id: str, access_token: str, request_function: type_get_request_function
) -> OrchestratorTestResponse:
    test_url = f"{API_BASE}/assessments/{test_id}"

    try:
        response = request_function(test_url, access_token)
        test_url = f"{DASHBOARD_URL}/r/test/{test_id}"

        return OrchestratorTestResponse(test_url=test_url, **response.json())

    except HTTPError as httpe:
        if httpe.response.status_code == 404:
            raise ValueError(f"Test with test_id {test_id=} not found!")
        else:
            raise httpe

    except Exception as e:
        raise e


# def get_attack_by_id(
#     attack_id: int, access_token: str, request_function: type_get_request_function
# ) -> OrchestratorAttackResponse:
#     attack_url = f"{DASHBOARD_URL}/r/attack/{attack_id}"
#     try:
#         response = request_function(attack_url, access_token)
#         response_data = response.json()
#         return OrchestratorAttackResponse(
#             **response_data, is_finished=response_data["state"] == 2
#         )

#     except HTTPError as httpe:
#         if httpe.response.status_code == 404:
#             raise ValueError(f"Attack with {attack_id=} not found!")
#         else:
#             raise httpe

#     except Exception as e:
#         raise e


def get_extra_config_from_env() -> Dict[str, Any]:
    config_str = os.getenv("MINDGARD_EXTRA_CONFIG")
    return cast(Dict[str, Any], json.loads(config_str)) if config_str else {}


def get_attack_pack_from_env() -> type_attack_pack:
    pack = os.environ.get("ATTACK_PACK", "sandbox")
    return cast(type_attack_pack, pack)


def setup_orchestrator_webpubsub_request(
    request: OrchestratorSetupRequest,
    access_token: str,
    request_function: type_post_request_function,
) -> OrchestratorSetupResponse:
    url = f"{API_BASE}/tests/cli_init"

    try:
        data = request_function(url, access_token, request.model_dump())
        url = data.json().get("url", None)
        groupId = data.json().get("groupId", None)
        if not url or not groupId:
            raise ValueError("Invalid response from orchestrator.")
        return OrchestratorSetupResponse(url=url, group_id=groupId)

    except HTTPError as e:
        raise ValueError(
            "Failed to get a response from orchestrator, response invalid!"
        )
