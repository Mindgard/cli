# Typing
import json
from typing import Optional
from .run_poll_display import type_ui_task_map

# Orchestrator
from .orchestrator import OrchestratorTestResponse, get_test_by_id, GetTestAttacksResponse

# Constants
from .constants import DASHBOARD_URL

# UI
from rich.progress import Progress
from rich.table import Table


def poll_and_display_test(
    access_token: str,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
    initial_test: GetTestAttacksResponse,
) -> Optional[GetTestAttacksResponse]:
    test_and_attacks = get_test_by_id(access_token=access_token, test_id=initial_test.test.id)

    if len(ui_task_map.keys()) == 0:
        for item in test_and_attacks.items:
            ui_task_map[item.attack.id] = ui_task_progress.add_task(
                f"Attack {item.attack.attack_name}", total=1, status="[chartreuse1]queued"
            )

    for item in test_and_attacks.items:
        task_id = ui_task_map[item.attack.id]
        if item.attack.status == 2:
            ui_task_progress.update(task_id, completed=1, status="[chartreuse3]success")
        elif item.attack.status == -1:
            ui_task_progress.update(task_id, completed=1, status="[red3]failed")
        elif item.attack.status == 1:
            ui_task_progress.update(task_id, status="[orange3]running")

    if test_and_attacks.test.has_finished is False:
        return None
    return test_and_attacks


def output_test_table(
    json_out: bool,
    test: GetTestAttacksResponse,
    risk_threshold: int,
) -> Optional[Table]:
    if json_out:
        print(json.dumps(test.raw, indent=4))
        return None
    else:
        table = Table(title=f"Results - {DASHBOARD_URL}/r/test/{test.test.id}", width=80)
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Flagged Events", justify="right", style="green")

        for item in test.items:
            if item.attack.status != 2:
                name = f"Error running '{item.attack.attack_name}'"
                risk_str = "n/a"
                emoji = "❗️"
            else:
                try:
                    flagged_to_total_ratio = item.attack.flagged_events / item.attack.total_events
                except ZeroDivisionError:
                    flagged_to_total_ratio = 0

                name = item.attack.attack_name
                risk_str = f"{item.attack.flagged_events} / {item.attack.total_events}"
                emoji = "❌‍" if flagged_to_total_ratio >= (risk_threshold / 100.0) else "✅️"

            table.add_row(emoji, name, risk_str)

        return table
