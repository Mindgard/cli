import json

from pytest import CaptureFixture
from ...src.mindgard.__main__ import attackcategories


def test_attackcategories(capfd: CaptureFixture[str]) -> None:
    res_json = attackcategories(json_format=True)
    assert res_json is not None
    res_json.raise_for_status()
    assert res_json.status_code == 200
    out_json, _ = capfd.readouterr()
    try:
        json.loads(out_json) 
    except json.JSONDecodeError:
        assert False, "Output is not a valid JSON"
        
    res = attackcategories(json_format=False)
    assert res is not None
    assert res.status_code == 200
    out, _ = capfd.readouterr()
    assert len(out.splitlines()) > 2

    assert out_json != out
