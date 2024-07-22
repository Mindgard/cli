import json
from typing import Optional
from rich.console import Console, Group

from rich.panel import Panel
from rich.align import Align

from ..utils import CliResponse

from ..auth import require_auth

from ..orchestrator import get_test_by_id, get_tests
from ..api_service import api_get


@require_auth
def list_tests(access_token: str, json_format: bool, test_id: Optional[str]) -> CliResponse:
    """
    Run the command.

    Returns int of exit code
    """

    console = Console()

    if test_id is None:
        tests_res = get_tests(access_token, request_function=api_get)
    else:
        tests_res = [
            get_test_by_id(
                test_id=test_id, access_token=access_token, request_function=api_get
            )
        ]

    if json_format is True:
        print(json.dumps(tests_res))
    else:
        for test in tests_res:
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

            def bold(input: str) -> str:
                return "[b]" + input + "[/b]"

            layout = Group(
                Align.center(bold(test.mindgardModelName)),
                "Total tests: " + bold(str(138)),
                "Last test:",
                "  model name: " + bold(test.mindgardModelName),
                "  tested at: " + bold(test.createdAt),
                "  threat level: " + bold(risk_text),
                "  risk score: " + bold(str(score)),
                f"  details: {test.test_url}",
            )
            panel = Panel(layout)

            console.print(panel)

    return CliResponse(0)
