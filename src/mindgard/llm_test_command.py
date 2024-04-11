
import json
import sys
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich import print_json

from .wrappers import ModelWrapper

from .utils import CliResponse

from .auth import require_auth
from .api_service import ApiService

TEST_POLL_INTERVAL = 5

class LLMTestCommand():
    """
    Command to execute a single test and watch the results
    """

    def __init__(self, api_service: ApiService, model_wrapper:ModelWrapper, poll_interval:float = TEST_POLL_INTERVAL) -> None:
        self._api = api_service
        self._model_wrapper = model_wrapper
        self._poll_interval = poll_interval
        
    def run_inner(self, access_token:str, target:str, json_format:bool, risk_threshold:int) -> CliResponse:
        progress_console = Console(file=sys.stderr)
        output_console  = Console()

        prompts_resp = self._api.fetch_llm_prompts(access_token)
        attacks = prompts_resp["attacks"]

        overall_total = 0
        for attack in attacks:
            overall_total += len(attack["jailbreakPrompts"])

        attacks_progress = Progress(console=progress_console)
        all_attacks_progress = attacks_progress.add_task("all", total=overall_total)
        attacks_task_map: Dict[str, TaskID] = {}
        for attack in attacks:
            attack_name = attack["name"]
            attacks_task_map[attack_name] = attacks_progress.add_task(f"attack {attack_name}", total=len(attack["jailbreakPrompts"]))

        with attacks_progress:
            for attack in prompts_resp["attacks"]:
                attack_name = attack["name"]
                for prompt_obj in attack["jailbreakPrompts"]:
                    res = self._model_wrapper(prompt=prompt_obj["prompt"])
                    prompt_obj["answer"] = res

                    attacks_progress.advance(attacks_task_map[attack_name])
                    attacks_progress.advance(all_attacks_progress)

        prompts_resp["target"] = target
        submit_responses_resp = self._api.submit_llm_responses(access_token, responses=prompts_resp)
         
        test_res = self._api.get_test(access_token, test_id=submit_responses_resp["id"])
        test_id = test_res["id"]

        if json_format is True:
            print_json(data=test_res)
            # output_console.print(json.dumps(test_res))
        else:
            table = Table(title=f"Results - https://sandbox.mindgard.ai/r/test/{test_id}", width=80)
            table.add_column("Pass", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Risk", justify="right", style="green")

            for attack in test_res["attacks"]:
                risk = attack["risk"]
                emoji = "❌" if risk > risk_threshold else "✅"
                table.add_row(emoji, attack["attack"], str(risk))

            output_console.print(table)

        return CliResponse(self.calculate_exit_code(test_res=test_res,risk_threshold=risk_threshold))
    
    @require_auth
    def run(self, access_token:str, target:str, json_format:bool, risk_threshold:int) -> CliResponse:
        """
        Run the command.

        Returns int of exit code
        """
        return self.run_inner(access_token=access_token, json_format=json_format, target=target, risk_threshold=risk_threshold)
    
    def calculate_exit_code(self, test_res:Dict[str, Any], risk_threshold:int) -> int:
        if test_res["risk"] > risk_threshold:
            return 1
        else:
            return 0
