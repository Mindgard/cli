from .auth import require_auth
from .utils import CliResponse

from typing import Callable, Any


# type alias
type_submit_function = Callable[[str], Any]
type_polling_function = Callable[[str, Any], int]


@require_auth
def cli_run(
    submit_function: type_submit_function,
    polling_function: type_polling_function,
    # This needs to be the last arg?
    access_token: str,
) -> CliResponse:

    submit_result = submit_function(access_token)
    exit_code = polling_function(access_token, submit_result)

    return CliResponse(exit_code)
