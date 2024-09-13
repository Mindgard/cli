"""
Temporary module to split off the __main__ for test execution using
new library system.
"""

from threading import Thread
from typing import Dict
from mindgard.auth import load_access_token
from mindgard.constants import API_BASE
from mindgard.test import LLMModelConfig, Test, TestConfig
from mindgard.test_ui import TestUI
from mindgard.utils import print_to_stderr
from mindgard.wrappers.llm import LLMModelWrapper


def run_test(final_args:Dict[str, str], model_wrapper: LLMModelWrapper):
  access_token = load_access_token()
  if not access_token:
      print_to_stderr("\033[1;37mRun `mindgard login`\033[0;0m to authenticate.")
      exit(2)

  test_config = TestConfig(
      api_base=API_BASE,
      api_access_token=access_token,
      target=final_args["target"],
      attack_source="user",
      parallelism=int(final_args["parallelism"]),
      model=LLMModelConfig(
          wrapper=model_wrapper,
          system_prompt=final_args["system_prompt"],
      )
  )

  test = Test(test_config)
  test_ui = TestUI(test)

  test_thread = Thread(target=test.run)
  test_thread.start()

  test_ui.run()
  test_thread.join()
  exit(1)