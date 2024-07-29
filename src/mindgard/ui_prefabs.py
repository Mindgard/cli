# Typing
import json
from typing import Optional
from .run_poll_display import type_ui_task_map

# Orchestrator
from .orchestrator import OrchestratorTestResponse, get_test_by_id

# Constants
from .constants import DASHBOARD_URL

# UI
from rich.progress import Progress
from rich.table import Table


def poll_and_display_test(
    access_token: str,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
    initial_test: OrchestratorTestResponse,
) -> Optional[OrchestratorTestResponse]:
    test = get_test_by_id(access_token=access_token, test_id=initial_test.id)

    if len(ui_task_map.keys()) == 0:
        for attack in test.attacks:
            ui_task_map[attack.id] = ui_task_progress.add_task(
                f"Attack {attack.attack}", total=1, status="[chartreuse1]queued"
            )

    for attack in test.attacks:
        task_id = ui_task_map[attack.id]
        if attack.state == 2:
            ui_task_progress.update(task_id, completed=1, status="[chartreuse3]success")
        elif attack.state == -1:
            ui_task_progress.update(task_id, completed=1, status="[red3]failed")
        elif attack.state == 1:
            ui_task_progress.update(task_id, status="[orange3]running")

    if test.hasFinished is False:
        return None
    return test


def output_test_table(
    json_out: bool,
    test: OrchestratorTestResponse,
    risk_threshold: int,
) -> Optional[Table]:
    if json_out:
        print(test.model_dump_json())
        return None
    else:
        table = Table(title=f"Results - {DASHBOARD_URL}/r/test/{test.id}", width=80)
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Risk", justify="right", style="green")

        for attack in test.attacks:
            if attack.state != 2:
                name = f"Error running '{attack.attack}'"
                risk_str = "n/a"
                emoji = "❗️"
            else:
                name = attack.attack
                risk_str = str(attack.risk)
                emoji = "❌‍" if attack.risk > risk_threshold else "✅️"

            table.add_row(emoji, name, risk_str)

        return table
