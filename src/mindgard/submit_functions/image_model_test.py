from ..run_poll_display import type_submit_func, type_polling_func

from ..orchestrator import (
    OrchestratorTestResponse,
)


def image_test_submit_factory() -> type_submit_func:

    def image_test_submit(access_token: str) -> OrchestratorTestResponse:
        return None

    return image_test_submit


def image_test_polling_factory(risk_threshold: int) -> type_polling_func:
    def run_local_image_test_polling(
        access_token: str, test_res: OrchestratorTestResponse
    ) -> int:
        return 0

    return run_local_image_test_polling
