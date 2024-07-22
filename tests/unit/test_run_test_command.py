# from typing import NamedTuple
# from unittest.mock import MagicMock
# import pytest
# from pytest_snapshot.plugin import Snapshot # type: ignore
# from ...src.mindgard.api_service import ApiService
# from ...src.mindgard.commands.run_test import RunTestCommand

# class Fixture(NamedTuple):
#     api_service: ApiService
#     access_token: str
#     model_name: str

# def _helper_fixtures() -> Fixture:
#     model_name = "mymodel"
#     access_token = "atoken"
#     api_service = ApiService()
#     api_service.submit_test = MagicMock(return_value={
#         "id" : "test_id"
#     })
#     api_service.get_test = MagicMock(return_value={
#         "id" : "test_id",
#         "hasFinished" : True,
#         "risk" : 50,
#         "attacks" : [{
#             "id" : "attack_id1",
#             "attack" : "myattack",
#             "state": 2,
#             "risk": 12,
#         }]
#     })
#     return Fixture(
#         api_service=api_service,
#         model_name=model_name,
#         access_token=access_token,
#     )


# def test_json_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot):
#     fixture = _helper_fixtures()

#     test_cmd = RunTestCommand(api_service=fixture.api_service, poll_interval=0.1)
#     res = test_cmd.run_inner(
#         access_token=fixture.access_token,
#         model_name=fixture.model_name,
#         json_format=True,
#         risk_threshold=80,
#     )

#     assert res.code() == 0
#     captured = capsys.readouterr()
#     stdout = captured.out
#     snapshot.assert_match(stdout, 'stdout.json')

# def test_text_output(capsys: pytest.CaptureFixture[str], snapshot:Snapshot):
#     fixture = _helper_fixtures()

#     test_cmd = RunTestCommand(api_service=fixture.api_service, poll_interval=0.1)
#     res = test_cmd.run_inner(
#         access_token=fixture.access_token,
#         model_name=fixture.model_name,
#         json_format=False,
#         risk_threshold=80,
#     )

#     assert res.code() == 0
#     captured = capsys.readouterr()
#     stdout = captured.out
    # TODO because the dashboard url is now dynamic this assertion has to be fixed
    # snapshot.assert_match(stdout, 'stdout.txt') # type: ignore

# def test_risk_threshold_pass():
#     fixture = _helper_fixtures()

#     test_cmd = RunTestCommand(api_service=fixture.api_service, poll_interval=0.1)
#     res = test_cmd.run_inner(
#         access_token=fixture.access_token,
#         model_name=fixture.model_name,
#         json_format=False,
#         risk_threshold=80,
#     )

#     assert res.code() == 0

# def test_risk_threshold_fail():
#     fixture = _helper_fixtures()

#     test_cmd = RunTestCommand(api_service=fixture.api_service, poll_interval=0.1)
#     res = test_cmd.run_inner(
#         access_token=fixture.access_token,
#         model_name=fixture.model_name,
#         json_format=False,
#         risk_threshold=0,
#     )

#     assert res.code() == 1
