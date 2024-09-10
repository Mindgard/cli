from threading import Thread
from pytest_snapshot.plugin import Snapshot # type: ignore
from rich.console import Console
from mindgard.test import AttackState, TestState
from mindgard.test_ui import TestUI

class FakeTest():
  def __init__(self, state:TestState):
    self._state = state

  def run(self) -> None:
    self._state.set_started()
    self._state.set_submitting_test()
    self._state.set_attacking("my_test_id", attacks=[
      AttackState(id="1", name="myattack1", state="queued", errored=False, passed=True,  risk=50),
      AttackState(id="2", name="myattack2", state="running", errored=False, passed=False, risk=80),
      AttackState(id="3", name="myattack3", state="completed", errored=True,  passed=None,  risk=None),
    ])

    self._state.add_exception(Exception("my 2nd exception"))
    self._state.add_exception(Exception("my 2nd exception"))
    self._state.add_exception(Exception("my 1st exception"))
    self._state.add_exception(Exception("my 1st exception"))

    self._state.set_test_complete("my_test_id", attacks=[
      AttackState(id="1", name="myattack1", state="completed", errored=False, passed=True,  risk=50),
      AttackState(id="2", name="myattack2", state="completed", errored=False, passed=False, risk=80),
      AttackState(id="3", name="myattack3", state="completed", errored=True,  passed=None,  risk=None),
    ])

def test_ui_complete(
    snapshot:Snapshot
):
  test_state = TestState()
  test = FakeTest(test_state)
  console = Console()
  test_ui = TestUI(test_state, console)

  t = Thread(target=test.run)
  t.start()

  with console.capture() as capture:
    test_ui.run()
  t.join()

  snapshot.assert_match(capture.get(), 'stdout.txt')