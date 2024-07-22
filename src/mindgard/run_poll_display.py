from .auth import require_auth
from .utils import CliResponse

from typing import Callable, Any, Dict


# type alias
type_submit_function = Callable[[str], Any]
type_polling_function = Callable[[str, Any], int]

# UI stuff
from rich.progress import Progress, SpinnerColumn, TaskID


@require_auth
def cli_run(
    submit_function: type_submit_function,
    polling_function: type_polling_function,
    # access_token cannot be the first arg it seems
    access_token: str,
    json_out: bool,
) -> CliResponse:

    submit_progress = Progress(
        "{task.description}",
        SpinnerColumn(finished_text="[green3] Submitted!"),
        auto_refresh=False,
        disable=json_out,
    )

    with submit_progress:
        task_id = submit_progress.add_task("Submitting test...", start=True)
        submit_result = submit_function(access_token)
        submit_progress.update(task_id, completed=100)

    exit_code = polling_function(access_token, submit_result)

    return CliResponse(exit_code)
