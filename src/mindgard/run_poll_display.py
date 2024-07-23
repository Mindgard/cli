from .auth import require_auth
from .utils import CliResponse

from typing import Callable, Any, Dict, Optional

import time

# UI
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn
from rich.table import Table
from rich.live import Live

# type alias
type_submit_func = Callable[[str], Any]
type_ui_task_map = Dict[str, TaskID]
# type_ui_task_create_func = Optional[Callable[[], type_ui_task_map]]
type_polling_func = Callable[
    [str, Any, type_ui_task_map, Progress, bool], Optional[int]
]


@require_auth
def cli_run(
    submit_func: type_submit_func,
    polling_func: type_polling_func,
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

    progress_table = Table.grid(expand=True)
    overall_task_progress = Progress()

    task_progress = Progress(
        "{task.description}",
        SpinnerColumn(finished_text="done"),
        TextColumn("{task.fields[status]}"),
    )
    task_map: type_ui_task_map = {}

    with submit_progress:
        task_id = submit_progress.add_task("Submitting...", start=True)
        submit_result = submit_func(access_token)
        submit_progress.update(task_id, completed=100)

    progress_table.add_row(overall_task_progress)
    progress_table.add_row(task_progress)

    exit_code = polling_func(
        access_token, submit_result, task_map, task_progress, json_out
    )
    tasks_to_run = len(task_progress.tasks)
    overall_task_id = overall_task_progress.add_task("Progress", total=tasks_to_run)
    with Live(progress_table, refresh_per_second=10):
        while exit_code is None:
            exit_code = polling_func(
                access_token, submit_result, task_map, task_progress, json_out
            )
            completed_tasks = sum(task.completed for task in task_progress.tasks)
            overall_task_progress.update(overall_task_id, completed=completed_tasks)
            time.sleep(1)

    return CliResponse(exit_code)
