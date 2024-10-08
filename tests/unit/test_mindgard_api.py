import requests_mock
from mindgard.constants import VERSION
from mindgard.mindgard_api import AttackResponse, MindgardApi



def test_fetch_test_data(requests_mock:requests_mock.Mocker):
    api_base=f"https://example.com/api/v1"
    test_id = "test_id"
    access_token = "access_token"
    additional_headers = {
        "myheader": "myvalue",
    }

    requests_mock.get(
        f"{api_base}/assessments/{test_id}", 
        status_code=200,
        json={
            'hasFinished': False,
            'risk': 44,
            'attacks':[
                {
                    'id': 'attack_id1',
                    'attack': 'myattack1',
                    'state': 2,
                    'risk': 34,
                    'some_ignored_field': 'ignored',
                },
                {
                    'id': 'attack_id2',
                    'attack': 'myattack2',
                    'state': -1,
                    'risk': 0,
                },
                {
                    'id': 'attack_id3',
                    'attack': 'myattack3',
                    'state': 0,
                    'risk': 0,
                },
                {
                    'id': 'attack_id4',
                    'attack': 'myattack4',
                    'state': 1,
                }
            ]
        }, # type: ignore
    )

    mindgard_api = MindgardApi()
    test_data = mindgard_api.fetch_test_data(
        api_base=api_base, 
        access_token=access_token, 
        additional_headers=additional_headers,
        test_id=test_id
    )

    assert requests_mock.last_request is not None, "should make a request to our mock"
    assert requests_mock.last_request.url == f"{api_base}/assessments/{test_id}"
    assert requests_mock.last_request.headers.get("Authorization") == f"Bearer {access_token}", "should set authorization header"
    assert requests_mock.last_request.headers.get("X-User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert requests_mock.last_request.headers.get("User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert requests_mock.last_request.headers.get("myheader") == "myvalue", "should set additional headers"

    assert test_data is not None
    assert test_data.has_finished is False
    assert len(test_data.attacks) == 4
    assert test_data.attacks[0] == AttackResponse(
        id="attack_id1",
        name="myattack1",
        state="completed",
        errored=False,
        risk=34,
    )
    assert test_data.attacks[1] == AttackResponse(
        id="attack_id2",
        name="myattack2",
        state="completed",
        errored=True,
        risk=None,
    )
    assert test_data.attacks[2] == AttackResponse(
        id="attack_id3",
        name="myattack3",
        state="queued",
        errored=None,
        risk=None,
    )
    assert test_data.attacks[3] == AttackResponse(
        id="attack_id4",
        name="myattack4",
        state="running",
        errored=None,
        risk=None,
    )
    assert test_data.risk == 44, "should set risk"

def test_fetch_test_data_garbage_response(requests_mock:requests_mock.Mocker):
    api_base=f"https://example.com/api/v1"
    test_id = "test_id"
    requests_mock.get(
        f"{api_base}/assessments/{test_id}", 
        status_code=200,
        text='garbage',
    )

    mindgard_api = MindgardApi()
    test_data = mindgard_api.fetch_test_data(
        api_base=api_base, 
        access_token="anything", 
        additional_headers=None,
        test_id=test_id
    )

    assert test_data is None


def test_fetch_test_data_non200_response(requests_mock:requests_mock.Mocker):
    api_base=f"https://example.com/api/v1"
    test_id = "test_id"
    requests_mock.get(
        f"{api_base}/assessments/{test_id}", 
        status_code=404,
        json={ 'hasFinished': True, 'attacks': [] }, # valid data ensures we validate that response is ignored
    )

    mindgard_api = MindgardApi()
    test_data = mindgard_api.fetch_test_data(
        api_base=api_base, 
        access_token="anything", 
        additional_headers=None,
        test_id=test_id
    )

    assert test_data is None

def test_fetch_test_data_missing_keys(requests_mock:requests_mock.Mocker):
    api_base=f"https://example.com/api/v1"
    test_id = "test_id"
    requests_mock.get(
        f"{api_base}/assessments/{test_id}", 
        status_code=200,
        json={ 'attacks': [] }, # missing hasFinished
    )

    mindgard_api = MindgardApi()
    test_data = mindgard_api.fetch_test_data(
        api_base=api_base, 
        access_token="anything", 
        additional_headers=None,
        test_id=test_id
    )

    assert test_data is None