import json

from pytest import CaptureFixture

from ...src.mindgard.tests import get_tests, run_test


def test_tests_list(capfd: CaptureFixture[str]) -> None:
    json_res = get_tests(json_format=True)
    assert json_res is not None
    json_res.raise_for_status()
    out_json, _ = capfd.readouterr()
    try:
        json.loads(out_json) 
    except json.JSONDecodeError:
        assert False, "Output is not a valid JSON"
        
    res = get_tests(json_format=False)
    assert res is not None
    res.raise_for_status()
    out, _ = capfd.readouterr()
    assert "------------------------" in out
    assert "attack_ids" in out


def test_run_tests_json(capfd: CaptureFixture[str]) -> None:
    res = run_test("cfp_faces", json_format=True)
    assert res is not None
    res.raise_for_status()
    out, _ = capfd.readouterr()
    try:
        json.loads(out)
    except json.JSONDecodeError:
        assert False, "Output is not a valid JSON"
    assert '{"id": "' in out


def test_run_tests(capfd: CaptureFixture[str]) -> None:
    res = run_test("cfp_faces", json_format=False)
    assert res is not None
    res.raise_for_status()
    out, _ = capfd.readouterr()
    assert "{'id':" in out 
    # TODO: test and develop in-progress situation


