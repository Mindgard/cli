from ..run_poll_display import type_submit_function, type_polling_function

from ..orchestrator import submit_sandbox_test, OrchestratorTestResponse, get_test_by_id

import time

from ..utils import print_to_stderr

POLL_INTERVAL_SECONDS = 3


def submit_sandbox_submit_factory(model_name: str) -> type_submit_function:

    def submit_sandbox_submit(access_token: str) -> OrchestratorTestResponse:
        return submit_sandbox_test(access_token=access_token, target_name=model_name)

    return submit_sandbox_submit


def submit_sandbox_polling_factory(risk_threshold: int) -> type_polling_function:
    def submit_sandbox_polling(
        access_token: str, test: OrchestratorTestResponse
    ) -> int:
        code = 0

        while not test.hasFinished:
            time.sleep(POLL_INTERVAL_SECONDS)
            test = get_test_by_id(test_id=test.id, access_token=access_token)

            for attack in test.attacks:
                if attack.state == 2:
                    print_to_stderr(
                        f"attack {attack.attack} completed successfully (risk: {attack.risk})!"
                    )
                elif attack.state == -1:
                    print_to_stderr(f"attack {attack.attack} failed!")
                if attack.risk > risk_threshold:
                    code = 1

        return code

    return submit_sandbox_polling
