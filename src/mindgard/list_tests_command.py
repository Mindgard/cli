
import json
from typing import Optional
from rich.console import Console, Group

from rich.panel import Panel
from rich.align import Align

from .utils import CliResponse

from .auth import require_auth
from .api_service import ApiService


class ListTestsCommand():
    
    def __init__(self, api_service: ApiService) -> None:
        self._api = api_service

    @require_auth
    def run(self, access_token:str, json_format:bool, test_id:Optional[str]) -> CliResponse:
        """
        Run the command.

        Returns int of exit code
        """

        console = Console()
        
        if test_id is None:
            tests_res = self._api.get_tests(access_token)
        else:
            tests_res = [self._api.get_test(access_token, test_id=test_id)]

        if json_format is True:
            print(json.dumps(tests_res))
        else:
            for test in tests_res:

                score = test["risk"]
                model_name = test["mindgardModelName"]
                url = test["url"]
                
                risk_text = 'Minimal'
                if score >= 90:
                    risk_text = 'Critical'
                elif score >= 66:
                    risk_text = 'High'
                elif score >= 40:
                    risk_text = 'Medium'
                elif score >= 20:
                    risk_text = 'Low'
                
                def bold(input:str) -> str:
                    return "[b]" + input + "[/b]"
                
                layout = Group(
                    Align.center(bold(model_name)),
                    "Total tests: " + bold(str(138)),
                    "Last test:", 
                    "  model name: " +  bold(model_name),
                    "  tested at: " + bold(test["createdAt"]),
                    "  threat level: " + bold(risk_text),
                    "  risk score: " + bold(str(score)),
                    f"  details: {url}"
                )
                panel = Panel(layout)
                
                
                console.print(panel)

        return CliResponse(0)



