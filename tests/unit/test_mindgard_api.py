from attr import dataclass
import pytest
import requests
import requests_mock
from requests import exceptions as requests_exceptions
from mindgard import mindgard_api as api
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

def build_test_attacks_data(
    has_finished:bool = False,
):
    return {
        "test": {
            "has_finished": has_finished,
        },
    }

def test_fetch_test_attacks(requests_mock:requests_mock.Mocker):    
    api_base=f"https://example.com/api/v1"
    test_id = "test-id"
    access_token = "my-access-token"
    additional_headers = {
        "myheader": "myvalue",
    }


    requests_mock.get(
        f"{api_base}/tests/{test_id}/attacks",
        status_code=200,
        json=build_test_attacks_data(),
    )

    mindgard_api = MindgardApi()

    mindgard_api.fetch_test_attacks(
        api_base=api_base,
        access_token=access_token,
        test_id=test_id,
        additional_headers=additional_headers,
    )

    assert requests_mock.last_request is not None, "should make a request to our mock"
    assert requests_mock.last_request.url == f"{api_base}/tests/{test_id}/attacks"
    assert requests_mock.last_request.headers.get("Authorization") == f"Bearer {access_token}", "should set authorization header"
    assert requests_mock.last_request.headers.get("X-User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert requests_mock.last_request.headers.get("User-Agent") == f"mindgard-cli/{VERSION}", "should set user agent"
    assert requests_mock.last_request.headers.get("myheader") == "myvalue", "should set additional headers"

def test_fetch_test_attacks_data(requests_mock:requests_mock.Mocker):
    api_base=f"https://example.com/api/v1"
    test_id = "test-id"
    access_token = "my-access-token"
    additional_headers:dict[str,str] = {}

    expect_has_finished = False

    requests_mock.get(
        f"{api_base}/tests/{test_id}/attacks",
        status_code=200,
        json=build_test_attacks_data(has_finished=expect_has_finished),
    )

    mindgard_api = MindgardApi()

    response = mindgard_api.fetch_test_attacks(
        api_base=api_base,
        access_token=access_token,
        test_id=test_id,
        additional_headers=additional_headers,
    )

    assert response is not None
    assert response.has_finished == expect_has_finished

@dataclass
class ExceptionTestCasse:
    id:str
    exception:Exception
    expected_exception_message: str


@pytest.mark.parametrize(
    "exception_test_case",
    [pytest.param(case, id=case.id) for case in [
        ExceptionTestCasse(
            id="requests_error",
            # spot check that we're extracting the nice name from requests exceptions
            exception=requests_exceptions.ConnectionError(),
            expected_exception_message="error calling api: ConnectionError",
        ),
        ExceptionTestCasse(
            id="requests_error_base",
            # check that we're handling all of them
            exception=requests_exceptions.RequestException(),
            expected_exception_message="error calling api: RequestException",
        ),
        ExceptionTestCasse(
            id="unknown exception",
            exception=Exception(),
            expected_exception_message="error calling api: unknown exception",
        ),
    ]]
)
def test_fetch_test_attacks_data_request_exceptions(
    requests_mock:requests_mock.Mocker,
    exception_test_case:ExceptionTestCasse,
):
    api_base=f"https://example.com/api/v1"
    test_id = "test-id"
    access_token = "my-access-token"
    additional_headers:dict[str,str] = {}
    
    requests_mock.get(
        f"{api_base}/tests/{test_id}/attacks",
        exc=exception_test_case.exception,
    )

    mindgard_api = api.MindgardApi()

    
    with pytest.raises(
        api.GeneralException, 
        match=exception_test_case.expected_exception_message
    ) as final_exception:
        mindgard_api.fetch_test_attacks(
            api_base=api_base,
            access_token=access_token,
            test_id=test_id,
            additional_headers=additional_headers,
        )
    
    assert final_exception.value.__cause__ is exception_test_case.exception, "the resulting exception should include the original exception"


def test_fetch_test_attacks_data_non200(
    requests_mock:requests_mock.Mocker,
):
    

    status_code = 400
    expected_exception_type = api.HttpStatusException
    expected_exception_message = "error calling api. expected 200, got: 400"

    api_base=f"https://example.com/api/v1"
    test_id = "test-id"
    access_token = "my-access-token"
    additional_headers:dict[str,str] = {}
    
    requests_mock.get(
        f"{api_base}/tests/{test_id}/attacks",
        status_code=status_code,
    )

    mindgard_api = api.MindgardApi()

    
    with pytest.raises(
        expected_exception_type,
        match=expected_exception_message,
    ):
        mindgard_api.fetch_test_attacks(
            api_base=api_base,
            access_token=access_token,
            test_id=test_id,
            additional_headers=additional_headers,
        )

def test_fetch_test_attacks_data_decode_error(
    requests_mock:requests_mock.Mocker,
):
    api_base=f"https://example.com/api/v1"
    test_id = "test-id"
    access_token = "my-access-token"
    additional_headers:dict[str,str] = {}
    
    requests_mock.get(
        f"{api_base}/tests/{test_id}/attacks",
        status_code=200,
        text='garbage',
    )

    mindgard_api = api.MindgardApi()

    with pytest.raises(
        api.GeneralException,
    ) as got_exception:
        mindgard_api.fetch_test_attacks(
            api_base=api_base,
            access_token=access_token,
            test_id=test_id,
            additional_headers=additional_headers,
        )

    assert isinstance(got_exception.value.__cause__, requests.JSONDecodeError)
    assert str(got_exception.value) == f"error decoding api response: {str(got_exception.value.__cause__)}"

def test_fetch_test_attacks_data_response_body_type_error(
    requests_mock:requests_mock.Mocker,
):
    api_base=f"https://example.com/api/v1"
    test_id = "test-id"
    access_token = "my-access-token"
    additional_headers:dict[str,str] = {}
    
    requests_mock.get(
        f"{api_base}/tests/{test_id}/attacks",
        status_code=200,
        json='garbage',
    )

    mindgard_api = api.MindgardApi()

    with pytest.raises(
        api.GeneralException,
    ) as got_exception:
        mindgard_api.fetch_test_attacks(
            api_base=api_base,
            access_token=access_token,
            test_id=test_id,
            additional_headers=additional_headers,
        )
    
    assert isinstance(got_exception.value.__cause__, TypeError)
    assert str(got_exception.value) == f"error parsing api response: {str(got_exception.value.__cause__)}"