
import json
from typing import Dict, Any
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TaskID

from .utils import CliResponse

from .auth import require_auth
from .api_service import ApiService

TEST_POLL_INTERVAL = 5
class RunTestCommand(): # called 'RunTest..' to avoid pytest thinking it's a test
    """
    Command to execute a single test and watch the results
    """
    
    def __init__(self, api_service: ApiService, poll_interval:float = TEST_POLL_INTERVAL) -> None:
        self._api = api_service
        self._poll_interval = poll_interval # poll interval is expose to speed up tests

    def submit_test_progress(self, progress:Progress, access_token:str, model_name:str) -> Dict[str,Any]:
        with progress:
            with ThreadPoolExecutor() as pool:
                task_id = progress.add_task("submitting test", start=True)

                future = pool.submit(self.submit_test_fetching_initial, access_token, model_name)
                while not future.done():
                    progress.update(task_id, refresh=True)
                    sleep(0.1)
                progress.update(task_id, completed=100)
                return future.result()

    def submit_test_fetching_initial(self, access_token:str, model_name:str) -> Dict[str, Any]:
        initial_resp = self._api.submit_test(access_token, model_name)
        return self._api.get_test(access_token, initial_resp["id"])
        
    def run_inner(self, access_token:str, model_name:str, json_format:bool, risk_threshold:int) -> CliResponse:
        if json_format:
            return self.run_json(access_token=access_token, model_name=model_name, risk_threshold=risk_threshold)

        submit_progress = Progress(
            "{task.description}",
            SpinnerColumn(
                finished_text=r"\[done]"
            ),
            auto_refresh=True
        )
        
        test_res: Dict[str, Any]
        with submit_progress:
            test_res = self.submit_test_progress(submit_progress, access_token=access_token, model_name=model_name)

        attacks = test_res["attacks"]
        test_id = test_res["id"]
        attack_count = len(attacks)

        overall_progress = Progress()
        overall_task = overall_progress.add_task("overall", total=attack_count)

        attacks_progress = Progress(
            "{task.description}",
            SpinnerColumn(
                finished_text=r"\[done]"
            ),
        )
        attacks_task_map: Dict[str, TaskID] = {}
        for attack in attacks:
            attacks_task_map[attack["id"]] = attacks_progress.add_task(f"attack {attack['attack']}", total=1)
        

        progress_table = Table.grid(expand=True)
        progress_table.add_row(
            overall_progress
        )
        progress_table.add_row(
            attacks_progress
        )

        with Live(progress_table, refresh_per_second=10):
            while not overall_progress.finished:
                sleep(self._poll_interval)
                test_res = self._api.get_test(access_token, test_id=test_id)

                for attack_res in test_res["attacks"]:
                    task_id = attacks_task_map[attack_res["id"]]
                    if attack_res["state"] == 2:
                        attacks_progress.update(task_id, completed=1)
                        
                completed = sum(task.completed for task in attacks_progress.tasks)
                overall_progress.update(overall_task, completed=completed)
        

        table = Table(title=f"Results - https://sandbox.mindgard.ai/r/test/{test_id}", width=80)
        table.add_column("Pass", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Risk", justify="right", style="green")

        for attack in test_res["attacks"]:
            risk = attack["risk"]
            emoji = "❌‍" if risk > risk_threshold else "✅️"
            table.add_row(emoji, attack["attack"], str(risk))


        console = Console()
        console.print(table)

        return CliResponse(self.calculate_exit_code(test_res=test_res,risk_threshold=risk_threshold))

    @require_auth
    def run(self, access_token:str, model_name:str, json_format:bool, risk_threshold:int) -> CliResponse:
        """
        Run the command.

        Returns int of exit code
        """
        return self.run_inner(access_token=access_token, json_format=json_format, model_name=model_name, risk_threshold=risk_threshold)


    def run_json(self, access_token:str, model_name:str, risk_threshold:int) -> CliResponse:
        test_res = self.submit_test_fetching_initial(access_token=access_token, model_name=model_name)
        test_id = test_res["id"]
        while test_res["hasFinished"] is False:
            sleep(self._poll_interval)
            test_res = self._api.get_test(access_token, test_id=test_id)

        print(json.dumps(test_res))
        return CliResponse(self.calculate_exit_code(test_res=test_res,risk_threshold=risk_threshold))


    def calculate_exit_code(self, test_res:Dict[str, Any], risk_threshold:int) -> int:
        if test_res["risk"] > risk_threshold:
            return 1
        else:
            return 0

