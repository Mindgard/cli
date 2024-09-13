"""
Integration test for Test and TestUI
"""
import platform
from threading import Thread
from typing import Any, Dict, Optional
from unittest import mock
from unittest.mock import Mock
from pytest_snapshot.plugin import Snapshot # type: ignore
from rich.console import Console
from mindgard.mindgard_api import AttackResponse, FetchTestDataResponse
from mindgard.test import LLMModelConfig, Test, TestConfig
from mindgard.test_ui import TestUI
from mindgard.wrappers.llm import Context, LLMModelWrapper, PromptResponse
from tests.unit.test_lib_test_implementation_provider import MockModelWrapper

# allow us to make assertions and capture test issues in background threads
class PropagatingThread(Thread):
    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs) # type: ignore
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret

# TODO: move to test utils
class MockModelWrapper(LLMModelWrapper):
    """
    A mock model wrapper that mirrors the input prepending with 'hello {input}'
    
    If a context is provided, it will also append the number of turns in the context: 'hello {input} {n}'
    """
    @classmethod
    def mirror(cls, input:str) -> str:
        return "hello " + input
    
    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        if with_context:
            res = self.mirror(content) + " " + str(len(with_context.turns))
            with_context.add(PromptResponse(prompt=content, response=res))
            return res
        return self.mirror(content)

def _helper_default_config(extra: Dict[str, Any] = {}) -> TestConfig:
    return TestConfig(
        api_base="https://test.internal",
        api_access_token="my access token",
        target = "my target",
        attack_pack = "my attack pack",
        attack_source = "my attack source",
        parallelism = 3,
        model = LLMModelConfig(
            wrapper=MockModelWrapper(),
            system_prompt = "my system prompt"
        ),
    )

# integration test between Test and TestUI, with only the implementations mocked
@mock.patch("mindgard.test.TestImplementationProvider")
def test_ui_complete(
    mock_provider:Mock,
    snapshot:Snapshot,
):
  mock_provider = mock_provider.return_value
  mock_provider.init_test.return_value = ("https://sandbox.mindgard.ai/r/test/my_test_id", "my_test_group_id")
  mock_provider.create_client.return_value = Mock()
  mock_provider.start_test.return_value = "my_test_id"

  mock_provider.poll_test.side_effect = [
     None,
      FetchTestDataResponse(
            has_finished=False,
            attacks=[
               AttackResponse(
                  id="1",
                  name="myattack1",
                  state="queued"
               ),
            ]
      ),
      FetchTestDataResponse(
            has_finished=True,
            attacks=[
               AttackResponse(
                  id="1",
                  name="myattack1",
                  state="completed",
                  errored=False,
                  risk=50,
               ),
               AttackResponse(
                  id="2",
                  name="myattack2",
                  state="completed",
                  errored=False,
                  risk=80,
               ),
               AttackResponse(
                  id="3",
                  name="myattack3",
                  state="completed",
                  errored=True,
                  risk=None,
               ),
            ]
      )
  ]
  
  test = Test(_helper_default_config(), poll_period_seconds=0.01)
  console = Console()
  test_ui = TestUI(test, console)

  t = PropagatingThread(target=test.run)
  t.start()

  with console.capture() as capture:
    test_ui.run()
    t.join() # wait for test to finish without exception before exiting

  captured_output = capture.get()

  # snapshot provides visual clue to review complete changes, but they render differently
  # in windows
  assert "Results - https://sandbox.mindgard.ai/r/test/my_test_id" in captured_output
  assert "Attack myattack1 done success" in captured_output
  assert "Attack myattack3 done failed" in captured_output
  assert "Error running 'myattack3'" in captured_output
  if platform.system() != "Windows":
    snapshot.assert_match(captured_output, 'stdout.txt')