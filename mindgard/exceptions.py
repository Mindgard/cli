import logging

# OpenAI exceptions

# Typing
from typing import Callable, Dict, Literal, Optional, Type
from requests import status_codes, HTTPError



class MGException(Exception):
    def __init__(self, message: str = "exception") -> None:
        super().__init__(self)
        self.message = message

    def __str__(self) -> str:
        return self.message


# Other Exceptions
class Uncontactable(MGException):
    pass


# HTTP-like Exceptions
class HTTPBaseError(MGException):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code: int = status_code
        self.status_message: str = "<unknown>"
        try:
            self.status_message = status_codes._codes[status_code][0]
        except:
            pass


class BadRequest(HTTPBaseError):
    pass


class Unauthorized(HTTPBaseError):
    pass


class Forbidden(HTTPBaseError):
    pass


class NotFound(HTTPBaseError):
    pass


class Timeout(HTTPBaseError):
    pass


class UnprocessableEntity(HTTPBaseError):
    pass


class FailedDependency(HTTPBaseError):
    pass


class RateLimitOrInsufficientCredits(HTTPBaseError):
    pass


class InternalServerError(HTTPBaseError):
    pass


class ServiceUnavailable(HTTPBaseError):
    pass


class EmptyResponse(MGException):
    pass


class NotImplemented(MGException):
    pass


class GatewayTimeout(HTTPBaseError): ...


msg_bad_request = "LLM provider received message that couldn't be handled."
msg_unauthorized = "User is not authorized to access this LLM provider resource"
msg_forbidden = "User is known but does not have permission to access this resource"
msg_not_found = "This resource was not found."
msg_timeout = "Timed out while trying to access resource"
msg_unprocessable = "Entity sent to LLM could not be processed."
msg_failed_dependency = "Failed Dependency"
msg_rate_limit_or_insufficient_credits = "Rate Limit or Insufficient Credits"
msg_internal_server_error = "Internal Server Error"
msg_service_unavailable = "Service Unavailable"
msg_gateway_timeout = "The server, acting as a gateway or proxy, didn't receive a timely response from an upstream server it needed to access to complete the request"

_status_code_exception_map: Dict[int, HTTPBaseError] = {
    400: BadRequest(msg_bad_request, 400),
    401: Unauthorized(msg_unauthorized, 401),
    403: Forbidden(msg_forbidden, 403),
    404: NotFound(msg_not_found, 404),
    408: Timeout(msg_timeout, 408),
    422: UnprocessableEntity(msg_unprocessable, 422),
    424: FailedDependency(msg_failed_dependency, 424),
    429: RateLimitOrInsufficientCredits(msg_rate_limit_or_insufficient_credits, 429),
    500: InternalServerError(msg_internal_server_error, 500),
    503: ServiceUnavailable(msg_service_unavailable, 503),
    504: GatewayTimeout(msg_gateway_timeout, 504),
}


def status_code_to_exception(status_code: int, actual_error: Optional[HTTPError] = None) -> HTTPBaseError:
    return _status_code_exception_map.get(
        status_code, HTTPBaseError("An unexpected error occurred:" + str(actual_error.response), status_code)
    )


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
    GatewayTimeout: "NoResponse",
}


def handle_exception_callback(
    exception: Exception,
    handle_visual_exception_callback: Optional[Callable[[str], None]],
) -> ErrorCode:
    # TODO - come take a look at this
    error_code: ErrorCode = exceptions_to_cli_status_codes.get(type(exception), "CLIError")
    callback_text = str(exception)

    if handle_visual_exception_callback:
        handle_visual_exception_callback(callback_text)

    logging.debug(exception)
    return error_code

