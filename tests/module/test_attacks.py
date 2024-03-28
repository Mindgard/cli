import json

from pytest import CaptureFixture

from ...src.mindgard.attacks import get_attacks
from .conftest import example_ids


def test_attacks(capfd: CaptureFixture[str]) -> None:
    res_json = get_attacks(json_format=True)
    assert res_json is not None
    res_json.raise_for_status()
    assert res_json.status_code == 200
    out_json, err = capfd.readouterr()
    assert not err
    try:
        json.loads(out_json) 
    except json.JSONDecodeError:
        assert False, "Output is not a valid JSON"
        
    res = get_attacks(json_format=False)
    assert res is not None
    assert res.status_code == 200
    out, err = capfd.readouterr()
    assert not err
    assert len(out.splitlines()) > 2

    assert out_json != out


def test_attack_id(capfd: CaptureFixture[str]) -> None:
    res_json = get_attacks(json_format=True, attack_id=example_ids["attack_id"])
    assert res_json is not None
    res_json.raise_for_status()
    assert res_json.status_code == 200
    out_json, err = capfd.readouterr()
    assert not err
    try:
        json.loads(out_json) 
    except json.JSONDecodeError:
        assert False, "Output is not a valid JSON"
        
    res = get_attacks(json_format=False, attack_id=example_ids["attack_id"])
    assert res is not None
    assert res.status_code == 200
    out, err = capfd.readouterr()
    assert not err
    assert len(out.splitlines()) > 2

    assert out_json != out
