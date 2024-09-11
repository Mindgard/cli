"""
Temporary module to split off the __main__ for test execution using
new library system.
"""

from threading import Thread
from typing import Dict
from rich.console import Console
from mindgard.auth import load_access_token
from mindgard.constants import API_BASE
from mindgard.test import LLMModelConfig, Test, TestConfig, TestImplementationProvider, TestState
from mindgard.test_ui import TestUI
from mindgard.utils import print_to_stderr


def run_test(final_args:Dict[str, str]):
  access_token = load_access_token()
  if not access_token:
      print_to_stderr("\033[1;37mRun `mindgard login`\033[0;0m to authenticate.")
      exit(2)

  test_state = TestState()
  test_implementation_provider = TestImplementationProvider(test_state)
  test_config = TestConfig(
      api_base=API_BASE,
      api_access_token=access_token,
      target=final_args["target"],
      attack_source="user",
      parallelism=int(final_args["parallelism"]),
      model=LLMModelConfig(
          wrapper=model_wrapper, # type:ignore # TODO: this can't be both
          system_prompt=final_args["system_prompt"],
      )
  )

  test = Test(test_config, test_implementation_provider)
  console = Console()
  test_ui = TestUI(test_state, console)

  t = Thread(target=test.run)
  t.start()

  test_ui.run()
  t.join()
  exit(1)