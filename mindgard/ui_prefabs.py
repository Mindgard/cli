# Typing
import json
from typing import Optional
from .run_poll_display import type_ui_task_map

# Orchestrator
from .orchestrator import ListAttacksResponse, OrchestratorTestResponse, TestResponse, get_test_by_id

# Constants
from .constants import DASHBOARD_URL

# UI
from rich.progress import Progress
from rich.table import Table


def poll_and_display_test(
    access_token: str,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
    initial_test: ListAttacksResponse,
) -> Optional[ListAttacksResponse]:
    test = get_test_by_id(access_token=access_token, test_id=initial_test.test.id)

    if len(ui_task_map.keys()) == 0:
        for attack_result_pair in test.items:
            attack = attack_result_pair.attack
            ui_task_map[attack.id] = ui_task_progress.add_task(
                f"Attack {attack.attack_name}", total=1, status="[chartreuse1]queued"
            )

    for attack_result_pair in test.items:
        attack = attack_result_pair.attack
        task_id = ui_task_map[attack.id]
        if attack.status == 2:
            ui_task_progress.update(task_id, completed=1, status="[chartreuse3]success")
        elif attack.status == -1:
            ui_task_progress.update(task_id, completed=1, status="[red3]failed")
        elif attack.status == 1:
            ui_task_progress.update(task_id, status="[orange3]running")

    if test.test.has_finished is False:
        return None
    return test


def output_test_table(
    json_out: bool,
    test: ListAttacksResponse,
    risk_threshold: int,
) -> Optional[Table]:
    if json_out:
        print(test.model_dump_json())
        return None
    else:
        table = Table(title=f"Results - {DASHBOARD_URL}/r/test/{test.test.id}", width=80)
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Flagged Events", justify="right", style="green")

        for attack_result_pair in test.items:
            if attack_result_pair.attack.status != 2:
                name = f"Error running '{attack_result_pair.attack.attack_name}'"
                risk_str = "n/a"
                emoji = "❗️"
            else:
                name = attack_result_pair.attack.attack_name
                risk_str = f"{attack_result_pair.attack.flagged_events} / {attack_result_pair.attack.total_events}"
                emoji = "❌‍" if (attack_result_pair.attack.flagged_events / attack_result_pair.attack.total_events) > 0.5 else "✅️"

            table.add_row(emoji, name, risk_str)

        return table
