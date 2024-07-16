# from .auth import require_auth


# class RunAgainstImageModel:
#     def __init__(self, api_service, model):
#         self.model = model
#         self.api_service = api_service

#         # find a way to get image here 


#     @require_auth
#     def run(self):
#         pass

import json
import logging
from typing import Dict, Any, Callable, Literal, Optional, List
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

from .constants import DASHBOARD_URL

# Networking
from azure.messaging.webpubsubclient import WebPubSubClient, WebPubSubClientCredential
from azure.messaging.webpubsubclient.models import OnGroupDataMessageArgs

# Types
from typing import Type

import time

from .utils import CliResponse

from .auth import require_auth

from .image_wrappers import ImageModelWrapper

TEST_POLL_INTERVAL = 5

class RunImageCommand:
    def __init__(
        self,
        model_wrapper: ImageModelWrapper,
        directory: str,
        parallelism: int,   
        poll_interval: float = TEST_POLL_INTERVAL,
    ) -> None:
        self._poll_interval = poll_interval  # poll interval is expose to speed up tests
        self._model_wrapper = model_wrapper
        self._parallelism = parallelism
        self._directory = directory

    @staticmethod
    def validate_args(args:Dict[str, Any]) -> None:
        # args must include non-zero values for 
        # target: str, json_format: bool, risk_threshold: int, system_prompt: str
        missing_args: List[str]= []
        if args['parallelism'] < 1:
            raise ValueError(f"--parallelism must be a positive integer")
        if len(missing_args) > 0:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")

    def start_reading_all_files(self, directory: str):
        import os
        
        for filename in os.listdir(directory):
            if filename.endswith('.jpeg'):
                try:
                    with open(os.path.join(directory, filename), 'rb') as f:
                        image_bytes = f.read()
                        for _ in range(0, 50):
                            preds = self._model_wrapper.infer(image = image_bytes)
                            print(preds)
                except Exception as e:
                    print(f"Error loading image {filename}: {e}")
        
        return True


    def submit_test_progress(
        self, progress: Progress) -> bool:
        with progress:
            with ThreadPoolExecutor() as pool:
                task_id = progress.add_task("Submitting test...", start=True)

                future = pool.submit(
                    self.start_reading_all_files, directory = self._directory
                )

                while not future.done():
                    progress.update(task_id, refresh=True)
                    sleep(0.1)
                progress.update(task_id, completed=100)
                return future.result()

    def run_inner(
        self
    ) -> CliResponse:

        progress_table = Table.grid(expand=True)

        submit_progress = Progress(
            "{task.description}",
            SpinnerColumn(finished_text="[green3] Submitted!"),
            auto_refresh=True,
        )

        self.submit_test_progress(
            submit_progress,
        )

        return CliResponse(
            0
        )

    @require_auth
    def run(
        self,
        access_token: str,
    ) -> CliResponse:
        """
        Run the command.

        Returns int of exit code
        """
        return self.run_inner()