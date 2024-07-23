from typing import List, Optional

from ..run_poll_display import type_submit_func, type_polling_func

from ..api_service import api_get
from ..orchestrator import get_tests, get_test_by_id, OrchestratorTestResponse

from ..utils import print_to_stderr


def list_test_submit_factory(test_id: Optional[str] = None) -> type_submit_func:

    def list_test_submit(access_token: str) -> List[OrchestratorTestResponse]:
        if test_id is None:
            tests_res = get_tests(access_token, request_function=api_get)
        else:
            tests_res = [
                get_test_by_id(
                    test_id=test_id, access_token=access_token, request_function=api_get
                )
            ]

        return tests_res

    return list_test_submit


def list_test_polling_factory() -> type_polling_func:
    def list_test_polling(
        access_token: str, tests_response: List[OrchestratorTestResponse]
    ) -> int:
        for test in tests_response:
            risk_text = "Minimal"
            score = test.risk
            if score >= 90:
                risk_text = "Critical"
            elif score >= 66:
                risk_text = "High"
            elif score >= 40:
                risk_text = "Medium"
            elif score >= 20:
                risk_text = "Low"

            print_to_stderr(
                "Last test:",
                "  model name: " + test.mindgardModelName,
                "  tested at: " + test.createdAt,
                "  threat level: " + risk_text,
                "  risk score: " + str(score),
                f"  details: {test.test_url}",
            )

        return 0

    return list_test_polling
