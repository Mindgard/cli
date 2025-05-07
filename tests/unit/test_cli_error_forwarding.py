import dataclasses
from typing import List, Any
from unittest.mock import Mock
from mindgard.exceptions import exceptions_to_cli_status_codes, NotFound, BadRequest, Unauthorized, Forbidden, Timeout, \
    UnprocessableEntity, FailedDependency, RateLimitOrInsufficientCredits, InternalServerError, ServiceUnavailable, \
    msg_bad_request, status_code_to_exception, msg_unauthorized, msg_forbidden, \
    msg_not_found, msg_timeout, msg_unprocessable, msg_failed_dependency, msg_rate_limit_or_insufficient_credits, \
    msg_internal_server_error, msg_service_unavailable, ErrorCode, GatewayTimeout, msg_gateway_timeout, HTTPBaseError
from requests import HTTPError, Response

import pytest
from mindgard.exceptions import NotImplemented, handle_exception_callback

@dataclasses.dataclass
class HTTPErrorTestCase:
    status_code: int
    expected_exception: Any
    expected_exception_message: str
    expected_cli_status_code: ErrorCode

    def __str__(self):
        return f"{self.status_code}-{self.expected_exception.__name__}"


test_cases: List[HTTPErrorTestCase] = [
    HTTPErrorTestCase(status_code=400, expected_exception=BadRequest, expected_exception_message=msg_bad_request,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=401, expected_exception=Unauthorized, expected_exception_message=msg_unauthorized,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=403, expected_exception=Forbidden, expected_exception_message=msg_forbidden,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=404, expected_exception=NotFound, expected_exception_message=msg_not_found,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=408, expected_exception=Timeout, expected_exception_message=msg_timeout,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=422, expected_exception=UnprocessableEntity, expected_exception_message=msg_unprocessable,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=424, expected_exception=FailedDependency, expected_exception_message=msg_failed_dependency,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=429, expected_exception=RateLimitOrInsufficientCredits, expected_exception_message=msg_rate_limit_or_insufficient_credits,
                      expected_cli_status_code="RateLimited"),
    HTTPErrorTestCase(status_code=500, expected_exception=InternalServerError, expected_exception_message=msg_internal_server_error,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=503, expected_exception=ServiceUnavailable, expected_exception_message=msg_service_unavailable,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=504, expected_exception=GatewayTimeout, expected_exception_message=msg_gateway_timeout,
                      expected_cli_status_code="NoResponse"),
    HTTPErrorTestCase(status_code=455, expected_exception=HTTPBaseError, expected_exception_message="An unexpected error occurred:<Response [455]>",
                      expected_cli_status_code="CLIError")
]


@pytest.mark.parametrize("test_case", test_cases, ids=str)
def test_http_errors(test_case: HTTPErrorTestCase) -> None:
    try:
        response = Response()
        response.status_code = test_case.status_code
        raise HTTPError(response=response)
    except HTTPError as e:
        raised_exception = status_code_to_exception(e.response.status_code, actual_error=e)
        assert isinstance(raised_exception, test_case.expected_exception)
        assert raised_exception.message == test_case.expected_exception_message
        assert raised_exception.status_code == test_case.status_code

        cli_err_code_for_pinch = handle_exception_callback(raised_exception, None)
        assert cli_err_code_for_pinch == test_case.expected_cli_status_code


def test_non_http_error_code_handling() -> None:
    # TODO: when we can detect ContentPolicy errors, add a test for that
    assert handle_exception_callback(Exception(), None) == "CLIError"
    assert handle_exception_callback(NotImplemented(), None) == "NotImplemented"
    assert handle_exception_callback(ZeroDivisionError(), None) == "CLIError" # Example of an unexpected error

