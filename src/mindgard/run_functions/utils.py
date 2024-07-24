from ..orchestrator import OrchestratorTestResponse
from ..run_poll_display import type_ui_task_map, type_output_func
from ..ui_prefabs import poll_and_display_test, output_test_table

from typing import Optional
from rich.progress import Progress
from rich.table import Table


def model_test_polling(
    access_token: str,
    initial_test: OrchestratorTestResponse,
    ui_task_map: type_ui_task_map,
    ui_task_progress: Progress,
) -> Optional[OrchestratorTestResponse]:
    return poll_and_display_test(
        access_token,
        ui_task_map,
        ui_task_progress,
        initial_test,
    )


def model_test_output_factory(risk_threshold: int) -> type_output_func:
    def list_llm_test_output(
        test: OrchestratorTestResponse, json_out: bool
    ) -> Optional[Table]:
        return output_test_table(
            json_out=json_out, test=test, risk_threshold=risk_threshold
        )

    return list_llm_test_output
