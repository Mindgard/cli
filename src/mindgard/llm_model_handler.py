# Types
from typing import Literal, Dict, Type, Optional, Callable, List, Any, cast
from pydantic import BaseModel
from .wrappers import ModelWrapper, ContextManager
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

# Exceptions
from .exceptions import *

# Misc
from .run_command import (
    create_websocket_and_get_details,
    message_handler_function_factory,
    websocket_initial_connection,
)


class LLMArguments(BaseModel):
    system_prompt: str


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


# We're passing around a list as it can be remotely updated by the 'submitted_callback'.
# You're not able to return values from event fired functions usually, but this allows for it.
def submit_llm_test(
    access_token: str,
    target: str,
    parallelism: int,
    model_wrapper: ModelWrapper,
    visual_exception_callback: Callable[[str], None],
    modality_specific_args: BaseModel,
) -> List[str]:
    modality_specific_args = cast(LLMArguments, modality_specific_args)
    websocket_details = create_websocket_and_get_details(
        access_token=access_token,
        target=target,
        parallelism=parallelism,
        modality="text",
        payload={
            "system_prompt": modality_specific_args.system_prompt,
        },
    )

    context_manager = ContextManager()

    def error_callback(exception: Exception) -> ErrorCode:
        return handle_exception_callback(exception, visual_exception_callback)

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
