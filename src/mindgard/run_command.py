# Typing
from .utils import CliResponse
from typing import Any, Dict, Callable, Optional, Literal, Type, cast, List
from dataclasses import dataclass
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs
from .wrappers import ModelWrapper as TextModelWrapper, ContextManager
from pydantic import BaseModel

# Exceptions
from .exceptions import *

# Auth
from .auth import require_auth

# API
from .api_service import ApiService
import json

# Logging
import logging
from .utils import print_to_stderr

# Misc
from time import sleep

# Constants
from .constants import API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS


api_service = ApiService()


class LLMArguments(BaseModel):
    system_prompt: str


@dataclass
class WebsocketDetails:
    group_id: str
    url: str
    credentials: WebPubSubClientCredential
    ws_client: WebPubSubClient


ErrorCode = Literal[
    "CouldNotContact",
    "ContentPolicy",
    "CLIError",
    "NotImplemented",
    "NoResponse",
    "RateLimited",
    "NetworkIssue",
    "MaxContextLength",
]


exceptions_to_cli_status_codes: Dict[Type[Exception], ErrorCode] = {
    Uncontactable: "CouldNotContact",
    BadRequest: "NoResponse",  # not sure about this, we don't handle 400 atm
    Unauthorized: "NoResponse",
    Forbidden: "NoResponse",
    NotFound: "NoResponse",
    Timeout: "NoResponse",
    UnprocessableEntity: "NoResponse",  # this is currently being handled as a rate limit issue for some reason
    FailedDependency: "NoResponse",
    RateLimitOrInsufficientCredits: "RateLimited",
    InternalServerError: "NoResponse",
    ServiceUnavailable: "NoResponse",
    NotImplemented: "NotImplemented",
    EmptyResponse: "NoResponse",
}


def handle_exception_callback(
    exception: Exception,
    handle_visual_exception_callback: Optional[Callable[[str], None]],
) -> ErrorCode:
    # TODO - come take a look at this
    error_code: ErrorCode = exceptions_to_cli_status_codes.get(type(exception), "CLIError")  # type: ignore
    callback_text = str(exception)

    if handle_visual_exception_callback:
        handle_visual_exception_callback(callback_text)

    logging.debug(exception)
    return error_code


def llm_submit_attack(
    access_token: str,
    target: str,
    parallelism: int,
    system_prompt: str,
    model_wrapper: TextModelWrapper,
) -> List[str]:
    websocket_details = create_websocket_and_get_details(
        access_token=access_token,
        target=target,
        parallelism=parallelism,
        modality="text",
        system_prompt=system_prompt,
    )

    context_manager = ContextManager()

    def _handle_visual_exception_callback(data: str) -> None:
        print(data)

    def error_callback(exception: Exception) -> ErrorCode:
        return handle_exception_callback(exception, _handle_visual_exception_callback)

    submitted_id = [""]

    def submitted_callback(id: str) -> None:
        submitted_id[0] = id

    def request_callback(msg: OnGroupDataMessageArgs) -> Dict[str, Any]:
        context_id = msg.data["payload"].get("context_id", None)
        context = context_manager.get_context_or_none(context_id)
        content = msg.data["payload"]["prompt"]

        response: str = ""
        error_code: Optional[ErrorCode] = None

        try:
            # would pose being explicit with __call__ so we can ctrl+f easier, not a very clear shorthand
            response = model_wrapper.__call__(
                content=content,
                with_context=context,
            )
        except MGException as mge:
            error_code = error_callback(mge)
            if error_code == "CLIError":
                raise mge
        except Exception as e:
            raise e
        finally:
            # we always try to send a response
            return {
                "correlationId": msg.data["correlationId"],
                "messageType": "Response",
                "status": "ok",  # Deprecated but kept for compatibility
                "payload": {
                    "response": response,
                    "error": error_code,
                },
            }

    message_handler = message_handler_function_factory(
        request_callback=request_callback,
        submitted_callback=submitted_callback,
        ws_client=websocket_details.ws_client,
    )

    websocket_initial_connection(
        ws_client=websocket_details.ws_client,
        message_handler=message_handler,
        group_id=websocket_details.group_id,
    )

    return submitted_id


def websocket_initial_connection(
    ws_client: WebPubSubClient,
    message_handler: Callable[[OnGroupDataMessageArgs], None],
    group_id: str,
) -> None:
    ws_client.open()

    ws_client.subscribe("group-message", message_handler)  # type: ignore

    payload = {
        "correlationId": "",
        "messageType": "StartTest",
        "payload": {"groupId": group_id},
    }

    ws_client.send_to_group(group_name="orchestrator", content=payload, data_type="json")  # type: ignore


def message_handler_function_factory(
    request_callback: Callable[[OnGroupDataMessageArgs], Dict[str, str]],
    submitted_callback: Callable[[str], None],
    ws_client: WebPubSubClient,
) -> Callable[[OnGroupDataMessageArgs], None]:

    def recv_message_handler(msg: OnGroupDataMessageArgs) -> None:
        if msg.data["messageType"] == "Request":
            logging.debug(f"received request {msg.data=}")
            # TODO: Check if these exceptions are raised properly
            try:
                reply_data = request_callback(msg)
            except Exception as e:
                raise e
            logging.debug(f"sending response {reply_data=}")

            ws_client.send_to_group("orchestrator", reply_data, data_type="json")  # type: ignore
        elif (
            msg.data["messageType"] == "StartedTest"
        ):  # should be something like "Submitted", upstream change required.
            submitted_callback(msg.data["payload"]["testId"])
        else:
            pass

    return recv_message_handler


def create_websocket_and_get_details(
    access_token: str,
    target: str,
    parallelism: int,
    system_prompt: Optional[str],
    modality: str,
) -> WebsocketDetails:
    payload = {"target": target, "parallelism": parallelism, "modality": modality}
    # LLM experiments require system prompt before experiment can start, hence variably included
    if system_prompt is not None:
        payload["system_prompt"] = system_prompt

    ws_token_and_group_id = api_service.get_orchestrator_websocket_connection_string(
        access_token=access_token, payload=payload
    )

    url = ws_token_and_group_id.get("url", None)
    group_id = ws_token_and_group_id.get("groupId", None)

    if url is None:
        raise Exception("URL from API server missing for LLM forwarding!")
    if group_id is None:
        raise Exception("groupId from API server missing for LLM forwarding!")

    # Should fire the connect event on the orchestrator
    credentials = WebPubSubClientCredential(client_access_url_provider=url)
    ws_client = WebPubSubClient(credential=credentials)

    return WebsocketDetails(
        group_id=group_id, ws_client=ws_client, credentials=credentials, url=url
    )


def poll_for_successful_submission(submitted_id: List[str]) -> str:
    max_attempts = 30
    attempts_remaining = max_attempts
    while submitted_id[0] == "":
        sleep(1)
        attempts_remaining -= 1
        if attempts_remaining == 0:
            break

    # we're here if submitting was a success...
    if attempts_remaining != 0:
        return submitted_id[0]
    else:
        raise Exception(
            f"did not receive notification of test submitted within timeout ({max_attempts}s); failed to start test"
        )


def run_test_with_ui(
    access_token: str,
    target: str,
    parallelism: int,
    risk_threshold: int,
    model_wrapper: TextModelWrapper,
) -> CliResponse:
    return CliResponse(0)


def run_test_with_json_output(
    access_token: str,
    target: str,
    parallelism: int,
    risk_threshold: int,
    model_wrapper: TextModelWrapper,
    modality_specific_args: BaseModel,
) -> CliResponse:
    # there will be a switch of some kind for this:
    llm_args: LLMArguments = cast(LLMArguments, modality_specific_args)
    submitted_id = llm_submit_attack(
        access_token, target, parallelism, llm_args.system_prompt, model_wrapper
    )
    test_id = poll_for_successful_submission(submitted_id)
    test_res = api_service.get_test(access_token=access_token, test_id=test_id)
    while test_res.get("hasFinished", False) is False:
        test_res = api_service.get_test(access_token=access_token, test_id=test_id)
        sleep(API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS)

    print(json.dumps(test_res))
    return CliResponse(1 if test_res.get("risk", 100) > risk_threshold else 0)


# Decorator for authentication, automatically fetches access token for logged in user
@require_auth
def cli_run(
    access_token: str,
    json_format: bool,
    risk_threshold: int,
    target: str,
    parallelism: int,
    model_wrapper: TextModelWrapper,
    modality_specific_args: BaseModel,
) -> CliResponse:

    if json_format:
        return run_test_with_json_output(
            access_token=access_token,
            risk_threshold=risk_threshold,
            target=target,
            parallelism=parallelism,
            model_wrapper=model_wrapper,
            modality_specific_args=modality_specific_args,
        )
    else:
        return run_test_with_ui(
            access_token=access_token,
            risk_threshold=risk_threshold,
            target=target,
            parallelism=parallelism,
            model_wrapper=model_wrapper,
        )
