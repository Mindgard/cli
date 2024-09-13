from typing import List
from unittest.mock import Mock
from mindgard.exceptions import exceptions_to_cli_status_codes
from requests import HTTPError, Response

from mindgard.exceptions import NotImplemented, handle_exception_callback


def generate_mock_http_responses() -> List[Response]:
    responses: List[Response] = []
    for status_code in [404, 500, 444, 401, 429, 503, 418]: # Note 418 added to test for unexpected status codes
        response = Mock(spec=Response)
        response.status_code = status_code
        response.raise_for_status.side_effect = HTTPError(response=response)
        responses.append(response)
    return responses

mock_http_responses = generate_mock_http_responses()

def test_http_error_code_handling() -> None:
    for res in mock_http_responses:
        try:
            res.raise_for_status()
        except HTTPError as e:
            err_code = handle_exception_callback(e, None)
            if exceptions_to_cli_status_codes.get(err_code):
                assert res.status_code in exceptions_to_cli_status_codes[err_code]
            else:
                assert err_code == "CLIError" # We could not detect the error type from the http error

def test_non_http_error_code_handling() -> None:
    # TODO: when we can detect ContentPolicy errors, add a test for that
    assert handle_exception_callback(Exception(), None) == "CLIError"
    assert handle_exception_callback(NotImplemented(), None) == "NotImplemented"
    assert handle_exception_callback(ZeroDivisionError(), None) == "CLIError" # Example of an unexpected error

