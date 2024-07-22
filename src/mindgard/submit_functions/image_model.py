from ..run_poll_display import type_submit_function, type_polling_function

from ..orchestrator import (
    OrchestratorTestResponse,
)


def run_local_image_test_submit_factory() -> type_submit_function:

    def run_local_image_test_submit(access_token: str) -> OrchestratorTestResponse:
        return None

    return run_local_image_test_submit


def run_local_image_test_polling_factory(risk_threshold: int) -> type_polling_function:
    def run_local_image_test_polling(
        access_token: str, test_res: OrchestratorTestResponse
    ) -> int:
        return 0

    return run_local_image_test_polling
