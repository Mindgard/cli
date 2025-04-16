from argparse import Namespace
import csv
import os
import sys
import json
import toml

# Types
from typing import Any, Dict, List, Optional, Tuple
from mindgard.types import valid_llm_datasets

# Data models
from mindgard.orchestrator import OrchestratorTestResponse, GetTestAttacksResponse

# Constants
from mindgard.constants import (
    REPOSITORY_URL,
    VERSION,
)

# Requests
import requests


class CliResponse:
    def __init__(self, code: int):
        self._code = code

    def code(self) -> int:
        return self._code


def convert_test_to_cli_response(
    test: GetTestAttacksResponse, risk_threshold: int
) -> CliResponse:
    try:
        flagged_to_total_events_ratio = test.test.flagged_events / test.test.total_events
    except ZeroDivisionError:
        flagged_to_total_events_ratio = 0.0
    if flagged_to_total_events_ratio >= risk_threshold:
        return CliResponse(1)
    else:
        return CliResponse(0)


def print_to_stderr(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def print_to_stderr_as_json(dict: Any) -> None:
    print(json.dumps(dict), file=sys.stderr)


def version_to_tuple(version: str) -> Tuple[int, ...]:
    return tuple(map(int, version.split(".")))


def is_version_outdated() -> Optional[str]:
    try:
        res = requests.get(REPOSITORY_URL)
        res.raise_for_status()
        latest_version = res.json()["info"]["version"]
        latest_version_tuple = version_to_tuple(latest_version)
        current_version_tuple = version_to_tuple(VERSION)
        return latest_version if latest_version_tuple > current_version_tuple else None
    except Exception:
        return ""

def map_mode_to_attack_pack(mode: str) -> str:
    if mode == "exhaustive":
        return "large"
    elif mode == "thorough":
        return "medium"
    else:
        return "sandbox"
    
def parse_toml_and_args_into_final_args(
    config_file_path: Optional[str], args: Namespace
) -> Dict[str, Any]:
    config_file = config_file_path or "mindgard.toml"
    toml_args = {}
    try:
        with open(config_file, "r") as f:
            contents = f.read()
            toml_args = toml.loads(contents)
    except FileNotFoundError:
        if config_file_path is None:
            pass
        else:
            raise ValueError(
                f"Config file not found: {config_file=}. Check that the file exists on disk."
            )

    final_args = {
        k: v if v is not None else toml_args.get(k) or toml_args.get(k.replace("_", "-"))
        for k, v in vars(args).items()
    }
    
    final_args["api_key"] = final_args["api_key"] or os.environ.get(
        "MODEL_API_KEY", None
    )


    final_args["risk_threshold"] = final_args.get("risk_threshold") if final_args.get("risk_threshold") is not None else 50
    final_args["parallelism"] = final_args.get("parallelism") if final_args.get("parallelism") is not None else 5
    final_args["json"] = final_args.get("json") if final_args.get("json") is not None else False
    final_args["mode"] = final_args.get("mode") if final_args.get("mode") is not None else "fast"
    final_args["rate_limit"] = final_args.get("rate_limit") if final_args.get("rate_limit") is not None else 3600 # 60rps

    if(args.command == "test"):
        final_args["attack_pack"] = map_mode_to_attack_pack(args.mode)

    domain = final_args.get("domain", None)
    dataset = final_args.get("dataset", None)

    if dataset is None:
        if domain and (domain not in valid_llm_datasets.keys()):
            raise ValueError(f"Domain set in config file ({final_args['domain']}) was invalid! (choices: {[x for x in valid_llm_datasets]})")
        final_args["dataset"] = valid_llm_datasets.get(domain, None)
    else:

        if not os.path.exists(dataset):
            raise ValueError(f"Dataset {dataset} not found! Please provide a valid path to a dataset with new line separated prompts.")

        with open(dataset, "r") as datasets_file:
            try:
                datasets = csv.reader(datasets_file)
                all_rows = [line for line in datasets]
                lines = [line[0].strip() for line in all_rows]
            except csv.Error:
                raise ValueError(f"{dataset} is not a valid CSV file!")

            final_args["custom_dataset"] = json.dumps(lines)

    if final_args.get("force_multi_turn"):
        final_args["parallelism"] = 1
        

    return final_args

def check_expected_args(args: Dict[str, Any], expected_args: List[str]) -> None:
    missing_args: List[str] = []
    for arg in expected_args:
        if not args.get(arg):
            missing_args.append(f"`--{arg.replace('_', '-')}`")
    if missing_args:
        raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")
