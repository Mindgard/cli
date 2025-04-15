import os
import json

# Types
from pydantic import BaseModel, model_validator
from typing import Optional, Any, Dict, Literal, cast, List
from mindgard.types import type_post_request_function, type_get_request_function

# Constants
from mindgard.constants import API_BASE, DASHBOARD_URL

# Requests
from mindgard.api_service import (
    api_get,
    api_post,
)

# Exceptions
from requests.exceptions import HTTPError

# Tells pydantic to stop worrying about model_type namespace collision
BaseModel.model_config["protected_namespaces"] = ()


# Type aliases
from mindgard.types import type_orchestrator_source


class OrchestratorSetupRequest(BaseModel):
    target: str
    modelType: str
    system_prompt: Optional[str] = None
    dataset: Optional[str] = None
    custom_dataset: Optional[str] = None
    attackPack: Optional[str] = None
    attackSource: str
    parallelism: int
    labels: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    include: Optional[List[str]] = None
    prompt_repeats: Optional[int] = None

    @model_validator(mode="after")  # type: ignore
    def check_parallelism(self):
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
    source: type_orchestrator_source
    createdAt: str
    attacks: List[AttackModel]
    isCompleted: bool
    hasFinished: bool
    risk: int
    test_url: str


class GetTestAttacksAttack(BaseModel):
    id: str
    attack_name: str
    status: Literal[-1, 0, 1, 2]
    total_events: int
    flagged_events: int


class GetTestAttacksTest(BaseModel):
    has_finished: bool
    id: str
    model_name: str
    flagged_events: int
    total_events: int


class GetTestAttacksItem(BaseModel):
    attack: GetTestAttacksAttack


class GetTestAttacksResponse(BaseModel):
    items: list[GetTestAttacksItem]
    test: GetTestAttacksTest
    raw: Optional[Dict[str, Any]]


class GetTestListTest(BaseModel):
    id: str
    mindgard_model_name: str
    created_at: str
    flagged_events: int
    total_events: int

class GetTestListResponse(BaseModel):
    items: list[GetTestListTest]


def submit_sandbox_test(
    access_token: str,
    target_name: str,
    post_request_function: type_post_request_function = api_post,
    get_request_function: type_get_request_function = api_get,
) -> GetTestAttacksResponse:
    url = f"{API_BASE}/assessments"
    post_body = {"mindgardModelName": target_name}
    res = post_request_function(url, access_token, post_body)
    id = res.json().get("id", None)
    return get_test_by_id(
        test_id=id, access_token=access_token, request_function=get_request_function
    )


def get_tests(
    access_token: str, request_function: type_get_request_function = api_get
) -> GetTestListResponse:
    url = f"{API_BASE}/tests"

    try:
        response = request_function(url, access_token)
        return GetTestListResponse(**response.json())
    except Exception as e:
        raise e


def get_test_by_id(
    test_id: str,
    access_token: str,
    request_function: type_get_request_function = api_get,
) -> GetTestAttacksResponse:
    try:
        response = request_function(
            f"{API_BASE}/tests/{test_id}/attacks",
            access_token
        )
        data = response.json()
        return GetTestAttacksResponse(**response.json(), raw=data)

    except HTTPError as httpe:
        if httpe.response.status_code == 404:
            raise ValueError(f"Test with test_id {test_id=} not found!")
        else:
            raise httpe

    except Exception as e:
        raise e


def get_extra_config_from_env() -> Dict[str, Any]:
    config_str = os.getenv("MINDGARD_EXTRA_CONFIG")
    return cast(Dict[str, Any], json.loads(config_str)) if config_str else {}


def setup_orchestrator_webpubsub_request(
    request: OrchestratorSetupRequest,
    access_token: str,
    request_function: type_post_request_function = api_post,
) -> OrchestratorSetupResponse:
    url = f"{API_BASE}/tests/cli_init"

    try:
        payload = request.model_dump()
        extra_config = os.environ.get("MINDGARD_EXTRA_CONFIG", None)
        if extra_config is not None:
            payload["extraConfig"] = json.loads(extra_config)
        data = request_function(url, access_token, payload)
        url = data.json().get("url", None)
        groupId = data.json().get("groupId", None)
        if not url or not groupId:
            raise ValueError("Invalid response from orchestrator, missing websocket credentials.")
        return OrchestratorSetupResponse(url=url, group_id=groupId)

    except HTTPError as e:
        raise ValueError(
            f"Failed to get a response from orchestrator ({str(e)})!"
        )
