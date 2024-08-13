# OpenAI exceptions
from openai import (
    APIError,
    OpenAIError,
    ConflictError,
    NotFoundError,
    APIStatusError,
    RateLimitError,
    APITimeoutError,
    BadRequestError,
    APIConnectionError,
    AuthenticationError,
    InternalServerError as OPAIInternalServerError,
    PermissionDeniedError,
    UnprocessableEntityError,
    APIResponseValidationError,
)

# Typing
from typing import Dict
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


def openai_exception_to_exception(exception: OpenAIError) -> MGException:
    # if its an API error with a status code do this
    if isinstance(exception, APIStatusError):
        if exception.status_code == 422:
            err_message = "<none>"
            try:
                err_message = exception.response.json().get("error", err_message)
            except Exception:
                pass
            return UnprocessableEntity(
                f"Received 422 from provider: {err_message}", 422
            )
        return status_code_to_exception(exception.status_code)
    # otherwise do this, this needs to be refined more
    else:
        return EmptyResponse("response was empty or something")
