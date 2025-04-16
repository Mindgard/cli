from typing import Any, Callable, Dict, Literal, Optional, Tuple, get_args
from rich.progress import TaskID, Progress
from rich.table import Table
from dataclasses import dataclass
import requests


@dataclass
class ExceptionCountTuple:
    task_id: TaskID
    count: int


# Web pub sub message types
type_wps_message_type = Literal["StartTest", "StartedTest", "Response", "Request"]

# UI task map stores a name for a task along with its taskid to be updated in progress object
type_ui_task_map = Dict[str, TaskID]
# Stores an exception message with the task to update, and the number of times the exception has been thrown
type_ui_exception_map = Dict[str, ExceptionCountTuple]

# interfaces that submit, polling and output functions MUST MEET to be usable in run_poll_display.
type_submit_func = Callable[[str, type_ui_exception_map, Progress], Any]
type_polling_func = Callable[
    [str, Any, type_ui_task_map, Progress],
    Optional[Any],
]
type_output_func = Callable[[Any, bool], Optional[Table]]

# Orchestrator submit/request enums
type_orchestrator_attack_pack = Literal["sandbox", "threat_intel"]
type_orchestrator_source = Literal["threat_intel", "user", "mindgard"]
type_model_presets = Literal['huggingface-openai', 'openai-compatible', 'huggingface', 'openai', 'azure-openai', 'azure-aistudio', 'anthropic', 'tester', 'local']
type_model_presets_list: Tuple[type_model_presets, ...] = get_args(type_model_presets)

# Types for dependency injecting get/post request functions into over api_post and api_get in orchestrator
type_post_request_function = Callable[[str, str, Dict[str, Any]], requests.Response]
type_get_request_function = Callable[[str, str], requests.Response]

# Different log levels
log_levels = [
    "critical",
    "fatal",
    "error",
    "warn",
    "warning",
    "info",
    "debug",
    "notset",
]  # [n.lower() for n in logging.getLevelNamesMapping().keys()]

valid_llm_datasets = {
    "customerservice": "BadCustomer",
    "finance": "BadFinance",
    "legal": "BadLegal",
    "medical": "BadMedical",
    "injection": "SqlInjection",
    "rce": "Xss",
    "xss": "Xss",
}