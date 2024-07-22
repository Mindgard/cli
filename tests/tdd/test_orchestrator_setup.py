from src.mindgard.orchestrator import (
    OrchestratorSetupRequest,
    setup_orchestrator_webpubsub_request,
    get_attack_pack_from_env,
    get_extra_config_from_env,
)

from requests.exceptions import HTTPError
import requests
from pydantic import ValidationError
from typing import Any, Dict
import os

from unittest.mock import MagicMock, Mock


import pytest


def get_orchestrator_setup_request(parallelism: int = 1) -> Dict[str, Any]:
    os.environ["ATTACK_PACK"] = "threat_intel"
    os.environ["MINDGARD_EXTRA_CONFIG"] = '{"test": "test"}'
    return {
        "user": "test",
        "userAgent": "test",
        "targetModelName": "test",
        "url": "test",
        "model_type": "test",
        "attackSource": "test",
        "parallelism": parallelism,
        "attackPack": get_attack_pack_from_env(),
        "extraConfig": get_extra_config_from_env(),
    }


@pytest.mark.parametrize("system_prompt,dataset", [(None, None), ("test", "test")])  # type: ignore
def test_orchestrator_setup_request_validation_neither_both_error(
    system_prompt: Any, dataset: Any
) -> None:
    with pytest.raises(ValidationError):
        OrchestratorSetupRequest(
            system_prompt=system_prompt,
            dataset=dataset,
            **get_orchestrator_setup_request(1)
        )


@pytest.mark.parametrize("system_prompt,dataset", [("test", None), (None, "test")])  # type: ignore
def test_orchestrator_setup_request_validation_either(
    system_prompt: Any, dataset: Any
) -> None:
    OrchestratorSetupRequest(
        system_prompt=system_prompt,
        dataset=dataset,
        **get_orchestrator_setup_request(1)
    )


def test_orchestrator_setup_request_validation_dataset_parallelism() -> None:
    with pytest.raises(ValidationError):
        OrchestratorSetupRequest(
            system_prompt="wahhh",
            dataset="woahhh",
            **get_orchestrator_setup_request(-1)
        )


@pytest.mark.parametrize("orch_groupId,orch_url", [("test", "wss:aowijdawojidoaiw"), ("ijdaowijdoijawd-awodijaiwodjoia37812789319827", "wss:---aoiwojdo12378")])  # type: ignore
def test_setup_orchestrator_webpubsub_request_good_args(orch_groupId, orch_url) -> None:
    response_mock = Mock(spec=requests.Response)
    response_mock.json.return_value = {"groupId": orch_groupId, "url": orch_url}
    response = setup_orchestrator_webpubsub_request(
        OrchestratorSetupRequest(
            system_prompt="Hello useful llm", **get_orchestrator_setup_request(5)
        ),
        access_token="access_token",
        request_function=MagicMock(return_value=response_mock),
    )

    assert response.url is not None
    assert len(response.url) > 1
    assert "wss" in response.url

    assert response.group_id is not None
    assert len(response.group_id) > 1


@pytest.mark.parametrize("orch_groupId,orch_url", [(None, "wss:aowijdawojidoaiw"), ("ijdaowijdoijawd-awodijaiwodjoia37812789319827", None), (None, None), ("", "http:awjhdiawhu")])  # type: ignore
def test_setup_orchestrator_webpubsub_request_bad_args(orch_groupId, orch_url) -> None:

    with pytest.raises(ValueError):
        response_mock = Mock(spec=requests.Response)
        response_mock.json.return_value = {"groupId": orch_groupId, "url": orch_url}
        setup_orchestrator_webpubsub_request(
            OrchestratorSetupRequest(
                system_prompt="Hello useful llm", **get_orchestrator_setup_request(5)
            ),
            access_token="access_token",
            request_function=MagicMock(return_value=response_mock),
        )


@pytest.mark.parametrize("status_code", [(404), (400), (401), (403), (500)])  # type: ignore
def test_setup_orchestrator_webpubsub_request_raised_status_is_caught(
    status_code,
) -> None:
    with pytest.raises(ValueError) as ex:
        setup_orchestrator_webpubsub_request(
            OrchestratorSetupRequest(
                system_prompt="Hello useful llm", **get_orchestrator_setup_request(5)
            ),
            access_token="access_token",
            request_function=MagicMock(
                side_effect=HTTPError(response=MagicMock(status_code=status_code))
            ),
        )
        assert isinstance(ex, ValueError)
