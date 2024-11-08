import logging

# OpenAI exceptions

# Typing
from typing import Callable, Dict, Literal, Optional, Type
from requests import status_codes



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


_status_code_exception_map: Dict[int, HTTPBaseError] = {
    400: BadRequest("LLM provider received message that couldn't be handled.", 400),
    401: Unauthorized(
        "User is not authorized to access this LLM provider resource.", 401
    ),
    403: Forbidden(
        "User is known but does not have permission to access this resource.", 403
    ),
    404: NotFound("This resource was not found.", 404),
    408: Timeout("Timed out while trying to access resource", 408),
    422: UnprocessableEntity("Entity sent to LLM could not be processed.", 422),
    424: FailedDependency("Failed Dependency TODO", 424),
    429: RateLimitOrInsufficientCredits("Rate Limit or Insufficient Credits TODO", 429),
    500: InternalServerError("Internal Server Error TODO", 500),
    503: ServiceUnavailable("Service Unavailable TODO", 503),
}


def status_code_to_exception(status_code: int) -> HTTPBaseError:
    return _status_code_exception_map.get(
        status_code, HTTPBaseError("Error specifics unknown", -1)
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

