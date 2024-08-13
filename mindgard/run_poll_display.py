import time

# Auth
from .auth import require_auth

# Types
from typing import Any

# UI
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn
from rich.table import Table
from rich.live import Live
from rich.console import Console

# Type aliases
from .types import (
    type_submit_func,
    type_polling_func,
    type_output_func,
    type_ui_task_map,
    type_ui_exception_map,
)


def output_placeholder(_: str, __: bool) -> None:
    return None


@require_auth
def cli_run(
    submit_func: type_submit_func,
    polling_func: type_polling_func,
    # access_token cannot be the first arg it seems
    access_token: str,
    json_out: bool,
    submitting_text: str = "Submitting...",
    output_func: type_output_func = output_placeholder,
) -> Any:

    submit_progress = Progress(
        "{task.description}",
        SpinnerColumn(finished_text="[green3] Submitted!"),
        auto_refresh=False,
        disable=json_out,
    )

    progress_table = Table.grid(expand=True)
    overall_task_progress = Progress(disable=json_out)

    ui_task_progress = Progress(
        "{task.description}",
        SpinnerColumn(finished_text="done"),
        TextColumn("{task.fields[status]}"),
        disable=json_out,
    )
    ui_task_map: type_ui_task_map = {}

    ui_exceptions_progress = Progress("{task.description}", disable=json_out)
    ui_exception_map: type_ui_exception_map = {}

    with submit_progress:
        task_id = submit_progress.add_task(submitting_text, start=True)
        initial_result = submit_func(
            access_token, ui_exception_map, ui_exceptions_progress
        )
        submit_progress.update(task_id, completed=100)

    if not json_out:
        progress_table.add_row(overall_task_progress)
        progress_table.add_row(ui_task_progress)
        progress_table.add_row("")
        progress_table.add_row(ui_exceptions_progress)

    polled_result = polling_func(
        access_token, initial_result, ui_task_map, ui_task_progress
    )
    tasks_to_run = len(ui_task_progress.tasks)
    # don't show progress bar if there is only one task
    if tasks_to_run > 1:
        overall_task_id = overall_task_progress.add_task("Progress", total=tasks_to_run)

    with Live(progress_table, refresh_per_second=10):
        while polled_result is None:
            polled_result = polling_func(
                access_token, initial_result, ui_task_map, ui_task_progress
            )
            if tasks_to_run > 1:
                completed_tasks = sum(task.completed for task in ui_task_progress.tasks)
                overall_task_progress.update(overall_task_id, completed=completed_tasks)
            time.sleep(1)

    output_table = output_func(polled_result, json_out)
    if output_table:
        Console().print(output_table)

    return polled_result
