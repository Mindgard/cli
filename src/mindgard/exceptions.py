# OpenAI exceptions
from openai import BadRequestError, RateLimitError, PermissionDeniedError, AuthenticationError, NotFoundError, UnprocessableEntityError, OpenAIError

# Typing
from typing import Dict

class MGException(Exception):
    pass

# Other Exceptions
class Uncontactable(MGException):
    pass

# HTTP-like Exceptions
class HTTPBaseError(MGException):
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


_status_code_exception_map: Dict[int, HTTPBaseError] = {
    400: BadRequest("LLM provider received message that couldn't be handled."),
    401: Unauthorized("User is not authorized to access this LLM provider resource."),
    403: Forbidden("User is known but does not have permission to access this resource."),
    404: NotFound("This resource was not found."),
    408: Timeout("Timed out while trying to access resource"),
    422: UnprocessableEntity("Entity sent to LLM could not be processed."),
    424: FailedDependency("TODO"),
    429: RateLimitOrInsufficientCredits("TODO"),
    500: InternalServerError("TODO"),
    503: ServiceUnavailable("TODO")
}

def status_code_to_exception(status_code: int) -> HTTPBaseError:
    return _status_code_exception_map.get(status_code, HTTPBaseError("Error specifics unknown"))

def openai_exception_to_exception(exception: OpenAIError) -> HTTPBaseError:
    if isinstance(exception, BadRequestError): # 400
        return status_code_to_exception(400)
    elif isinstance(exception, RateLimitError): # 429
        return status_code_to_exception(429)
    elif isinstance(exception, PermissionDeniedError): # 403
        return status_code_to_exception(403)
    elif isinstance(exception, AuthenticationError): # 401
        return status_code_to_exception(401)
    elif isinstance(exception, NotFoundError): # 404
        return status_code_to_exception(404)
    elif isinstance(exception, UnprocessableEntityError): # 422
        return status_code_to_exception(422)
    return status_code_to_exception(-1)