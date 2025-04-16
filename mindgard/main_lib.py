"""
Temporary module to split off the __main__ for test execution using
new library system.
"""

from threading import Thread
from typing import Any, Dict

import requests
from mindgard.auth import clear_token, load_access_token
from mindgard.constants import API_BASE, EXIT_CODE_ERROR, EXIT_CODE_NOT_PASSED, EXIT_CODE_PASSED
from mindgard.test import LLMModelConfig, Test, TestConfig, UnauthorizedError
from mindgard.test_ui import TestUI
from mindgard.utils import print_to_stderr
from mindgard.wrappers.llm import LLMModelWrapper


def run_test(final_args:Dict[str, Any], model_wrapper: LLMModelWrapper):
  access_token = load_access_token()
  if not access_token:
      print_to_stderr("\033[1;37mRun `mindgard login`\033[0;0m to authenticate.")
      exit(EXIT_CODE_ERROR)

  test_config = TestConfig(
      api_base=API_BASE,
      api_access_token=access_token,
      target=final_args["target"],
      attack_source="user",
      dataset_domain=final_args.get('domain', None),
      parallelism=int(final_args["parallelism"]),
      model=LLMModelConfig(
          wrapper=model_wrapper,
          system_prompt=final_args["system_prompt"],
      ),
      exclude=final_args.get("exclude", None),
      include=final_args.get("include", None)
  )
  if (attack_pack := final_args.get("attack_pack")):
      test_config.attack_pack = attack_pack
  
  test = Test(test_config)
  test_ui = TestUI(test)

  # daemonize to prevent blocking the main thread's exit if test.run raises exception
  test_ui_thread = Thread(target=test_ui.run, name="TestUI")
  test_ui_thread.start()

  try:
      test.run()
  except UnauthorizedError:
      print_to_stderr(
          "Access token is invalid. Please re-authenticate using `mindgard login`"
      )
      clear_token()
      exit(EXIT_CODE_ERROR)
  except requests.HTTPError as e:
      if "Unauthorized" in str(e):
          print_to_stderr(
              "Access token is invalid. Please re-authenticate using `mindgard login`"
          )
          clear_token()
          exit(EXIT_CODE_ERROR)
      else:
          raise e

  test_ui_thread.join()
  
  if test.get_state().passed:
    exit(EXIT_CODE_PASSED)
  elif test.get_state().passed == False:
    exit(EXIT_CODE_NOT_PASSED)