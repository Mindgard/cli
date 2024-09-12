from typing import Dict
from rich.table import Table
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TaskID
from rich.live import Live
from mindgard.test import AttackState, Test
class TestUI():
  def __init__(self, test: Test, console:Console = Console()):
    self._console = console
    self._test = test

  def run(self) -> None:
    test = self._test
    
    # test.state_wait_for(lambda state: state.started)
    test.state_wait_for(lambda state: state.submitting)
    with Progress(
      "{task.description}",
      SpinnerColumn(finished_text="[green3] Submitted!"),
      auto_refresh=True,
      console=self._console,
    ) as submit_progress:
      submit_task_id = submit_progress.add_task("Submitting...", start=True)

      test.state_wait_for(lambda state: state.submitted)
          
      submit_progress.update(submit_task_id, completed=100)


    ##################################
    # the test is in progress
    progress_table = Table.grid(expand=True)

    overall_task_progress = Progress()
    exceptions_progress = Progress("{task.description}")
    
    attack_progress = Progress(
      "{task.description}",
      SpinnerColumn(finished_text="done"),
      TextColumn("{task.fields[status]}"),
    )

    progress_table.add_row(overall_task_progress)
    progress_table.add_row(attack_progress)
    progress_table.add_row("")
    progress_table.add_row(exceptions_progress)

    def task_update(attack_progress:Progress, task: TaskID, attack: AttackState) -> None:
      if attack.state == "completed":
        if attack.errored:
          attack_progress.update(task, status="[red3]failed", completed=1)
        else:
          attack_progress.update(task, status="[chartreuse3]success", completed=1)
      elif attack.state == "running":
        attack_progress.update(task, status="[yellow]running", completed=0)
      else:
        attack_progress.update(task, status="[chartreuse1]queued", completed=0)

    with test.state_wait_for(lambda state: len(state.attacks) > 0) as state:
      attack_id_task_map: Dict[str, TaskID] = {}
      for attack in state.attacks:
        attack_id_task_map[attack.id] = attack_progress.add_task(f"Attack {attack.name}", total=1)
        task_update(attack_progress, attack_id_task_map[attack.id], attack)

      attacks_progress = overall_task_progress.add_task("Progress", total=len(state.attacks))
      completed_attacks = sum(1 for attack in state.attacks if attack.state == "completed")
      overall_task_progress.update(attacks_progress, completed=completed_attacks)

      model_exception_task_map: Dict[str, TaskID] = {}
      model_exception_counts: Dict[str, int] = {}
      for model_exception in state.model_exceptions:
        name = str(model_exception)
        if model_exception_task_map.get(name) is None:
          model_exception_task_map[name] = exceptions_progress.add_task("")
          model_exception_counts[name] = 1
        else:
          model_exception_counts[name] += 1

      for name, task in model_exception_task_map.items():
        exceptions_progress.update(task, description=f"[dark_orange3][!!!] {name} x{model_exception_counts[name]}")
      

    with Live(progress_table, refresh_per_second=10, console=self._console):
      finished = False
      while not finished:
        state = test.get_state()
        for attack in state.attacks:
          task = attack_id_task_map[attack.id]
          task_update(attack_progress, task, attack)
        
        completed_attacks = sum(1 for attack in state.attacks if attack.state == "completed")
        overall_task_progress.update(attacks_progress, completed=completed_attacks)

        model_exception_counts: Dict[str, int] = {}
        for model_exception in state.model_exceptions:
          name = str(model_exception)
          if model_exception_task_map.get(name) is None:
            model_exception_task_map[name] = exceptions_progress.add_task("")
          if model_exception_counts.get(name) is None:
            model_exception_counts[name] = 1
          else:
            model_exception_counts[name] += 1
        for name, task in model_exception_task_map.items():
          exceptions_progress.update(task, description=f"[dark_orange3][!!!] {name} x{model_exception_counts[name]}")

        finished = state.test_complete
        if not finished:
          test.state_wait()

    ##################################
    # the test is complete
    final_state = test.get_state()
    table = Table(title=f"Results - https://sandbox.mindgard.ai/r/test/{final_state.test_id}", width=80)
    table.add_column("Pass", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Risk", justify="right", style="green")

    for attack in final_state.attacks:
      if attack.errored:
        name = f"Error running '{attack.name}'"
        risk_str = "n/a"
        emoji = "❗️"
      else:
        name = attack.name
        risk_str = str(attack.risk)
        emoji = "✅️" if attack.passed else "❌‍"

      table.add_row(emoji, name, risk_str)

    self._console.print(table)