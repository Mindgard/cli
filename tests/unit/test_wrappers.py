import re
from unittest import mock
from unittest.mock import MagicMock

from httpx import Response
from openai import OpenAIError, APIStatusError
import requests_mock

import pytest
from pytest_httpx import HTTPXMock
import httpx

import mindgard
from mindgard.exceptions import Uncontactable, UnprocessableEntity, EmptyResponse, HTTPBaseError, \
    Unauthorized
from mindgard.wrappers.llm import OpenAIWrapper, TestStaticResponder, ContextManager, APIModelWrapper, \
    get_llm_model_wrapper, Context, PromptResponse

from openai import AuthenticationError

_EXPECTED_308_MESSAGE = "Failed to contact model: model returned a 308 redirect that couldn't be followed."

EXAMPLE_CHAT_COMPLETION_RESPONSE = content_target = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4o-mini",
    "system_fingerprint": "fp_44709d6fcb",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "my message",
        },
        "logprobs": None,
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 9,
        "completion_tokens": 12,
        "total_tokens": 21,
        "completion_tokens_details": {
            "reasoning_tokens": 0,
            "accepted_prediction_tokens": 0,
            "rejected_prediction_tokens": 0
        }
    }
}

def test_static_responder_no_context() -> None:
    wrapper = TestStaticResponder(
        system_prompt="mysysprompt"
    )
    text = "myprompt"
    assert wrapper(text) == "TEST. prompted with: request=\'[start]sys: mysysprompt; next: myprompt[end]\'"


def test_static_responder_with_context() -> None:

    system_prompt = "mysysprompt"
    wrapper = TestStaticResponder(
        system_prompt,
    )

    context_manager = ContextManager()
    context1 = context_manager.get_context_or_none("1")
    context2 = context_manager.get_context_or_none("2")
    contextnull = context_manager.get_context_or_none(None)

    message1c1 = "myprompt-message1c1"
    message1c2 = "myprompt-message1c2"
    message2c1 = "myprompt-message2c1"
    message1cnull = "myprompt-message1cnull"

    assert wrapper(message1c1, with_context=context1) == "TEST. prompted with: request='[start]sys: mysysprompt; next: myprompt-message1c1[end]'"
    assert wrapper(message1c2, with_context=context2) == "TEST. prompted with: request='[start]sys: mysysprompt; next: myprompt-message1c2[end]'"
    assert wrapper(message1cnull, with_context=contextnull) == "TEST. prompted with: request='[start]sys: mysysprompt; next: myprompt-message1cnull[end]'"
    assert wrapper(message2c1, with_context=context1) == "TEST. prompted with: request=\"[start]sys: mysysprompt; user: myprompt-message1c1; assistant: TEST. prompted with: request='[start]sys: mysysprompt; next: myprompt-message1c1[end]'; next: myprompt-message2c1[end]\""

def test_get_llm_model_wrapper_preset_openai() -> None:
    wrapper = get_llm_model_wrapper(headers={}, preset="openai", api_key="test api key")
    assert isinstance(wrapper, OpenAIWrapper) 
    


def test_api_model_wrapper_no_context_no_settings_no_system_prompt() -> None:
    url = "https://example.com/somewhere"
    wrapper = APIModelWrapper(
        url
    )
    text = "myprompt"

    with requests_mock.mock() as m:
        mock = m.post(
            url,
            json="eh up",
        )
        assert wrapper(text) == '"eh up"'
        assert mock.last_request.json() == {"prompt":text}

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_api_model_wrapper_rate_limit(
    mock_throttle: mock.MagicMock
) -> None:
    url = "https://example.com/somewhere"
    wrapper = APIModelWrapper(
        url,
        system_prompt="mysysprompt",
        rate_limit=100
    )
    mock_throttle.assert_called_once_with(mock.ANY, rate_limit=100)
    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_tester_preset_rate_limits(
    mock_throttle: mock.MagicMock
) -> None:
    wrapper = TestStaticResponder(
        system_prompt="mysysprompt",
        rate_limit=100
    )
    mock_throttle.assert_called_once_with(mock.ANY, rate_limit=100)
    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value

def test_api_model_wrapper_no_context_no_settings() -> None:
    system_prompt = "mysysprompt"
    text = "myprompt"
    url = "https://example.com/somewhere"
    wrapper = APIModelWrapper(
        url,
        system_prompt=system_prompt
    )

    with requests_mock.mock() as m:
        mock = m.post(
            url,
            json="eh up",
        )
        assert wrapper(text) == '"eh up"'
        assert mock.last_request.json() == {"prompt":f"{system_prompt} {text}"}

def test_api_model_wrapper_no_context_with_template() -> None:
    system_prompt = "mysysprompt"
    text = "myprompt"
    request_template = '{"arbitrary":"{prompt}", "alsoarbitrary": "is {system_prompt}"}'
    url = "https://example.com/somewhere"
    wrapper = APIModelWrapper(
        url,
        system_prompt=system_prompt,
        request_template=request_template,
        selector="$.stuff[0].message"
    )

    with requests_mock.mock() as m:
        mock = m.post(
            url,
            json = {"stuff": [{"message":"eh up"}, "text"]} # a slightly pathological example to stretch the implementation
        )
        assert wrapper(text) == "eh up"
        assert mock.last_request.json() == {"alsoarbitrary": f"is {system_prompt}", "arbitrary":text}

def test_api_model_wrapper_with_context_with_template() -> None:
    header_key = "random"
    header_value = "thing"
    url = "https://example.com/somewhere"
    wrapper = APIModelWrapper(
        url,
        headers={header_key:header_value},
    )
    text = "myprompt"

    with requests_mock.mock() as m:
        mock = m.post(
            url,
            json="eh up",
        )
        assert wrapper(text) == '"eh up"'
        assert mock.last_request.headers[header_key] == header_value

def test_api_model_wrapper_does_not_support_multi_turn_by_default_due_to_interleving_requests() -> None:
    header_key = "random"
    header_value = "thing"
    url = "https://example.com/somewhere"
    
    wrapper = APIModelWrapper(
        url,
        headers={header_key:header_value},
    )

    with requests_mock.mock() as m:
        m.post(
            url,
            json="eh up",
        )
        context = Context()
        context.add(PromptResponse(prompt="Foo", response="Bar", duration_ms=1))
        with pytest.raises(mindgard.exceptions.NotImplemented):
            wrapper("hello", context)

def test_api_model_wrapper_can_support_multi_turn_in_stateful_api_scenarios() -> None:
    header_key = "random"
    header_value = "thing"
    url = "https://example.com/somewhere"
    wrapper = APIModelWrapper(
        url,
        headers={header_key:header_value},
        multi_turn_enabled=True
    )

    with requests_mock.mock() as m:
        m.post(
            url,
            json="eh up",
        )
        context = Context()
        context.add(PromptResponse(prompt="Foo", response="Bar", duration_ms=1))

        assert '"eh up"' == wrapper("hello", context)


def test_llm_local_model_wrapper_allow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = {"message":"my message"}
    wrapper = get_llm_model_wrapper(
        preset="local",
        url=url_redirect,
        selector="$.message",
        headers={},
        allow_redirects=True,
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})
        m.post(url_target, json=content_target, status_code=200)

        res = wrapper("a")
        assert res == "my message"

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 2, "default should follow redirects"
        assert m.last_request.url == url_target

def test_llm_local_model_wrapper_disallow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    wrapper = get_llm_model_wrapper(
        preset="local",
        url=url_redirect,
        selector="$.message",
        headers={},
        allow_redirects=False,
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})

        with pytest.raises(
            Uncontactable, 
            match=re.escape(_EXPECTED_308_MESSAGE)
        ):
            wrapper("a")
        
        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 1, "should not follow redirects"
        assert m.last_request.url == url_redirect

def test_llm_local_model_wrapper_default_allow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = {"message":"my message"}
    wrapper = get_llm_model_wrapper(
        preset="local",
        url=url_redirect,
        selector="$.message",
        headers={},
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})
        m.post(url_target, json=content_target, status_code=200)

        res = wrapper("a")
        assert res == "my message"

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 2, "default should follow redirects"
        assert m.last_request.url == url_target

def test_llm_huggingfaceopenai_model_wrapper_allow_redirects(httpx_mock: HTTPXMock) -> None:
    url_redirect = "https://example.com/redirect"
    url_redirect_expected = "https://example.com/redirect/v1/chat/completions"
    url_target = "https://example.com/target"
    url_target_expected = url_target
    content_redirect = {"nothing":"here"}

    wrapper = get_llm_model_wrapper(
        preset="huggingface-openai",
        api_key="test api key",
        url=url_redirect,
        headers={},
        allow_redirects=True,
    )

    httpx_mock.add_response(
        url=url_redirect_expected, 
        method="POST", 
        status_code=308, 
        headers={"Location":url_target}, 
        json=content_redirect
    )
    httpx_mock.add_response(
        url=url_target_expected, 
        method="POST", 
        status_code=200, 
        json=EXAMPLE_CHAT_COMPLETION_RESPONSE
    )

    res = wrapper("a")
    assert res == "my message"

    # we know it's processed the redirect if we got the two requests
    assert len(httpx_mock.get_requests()) == 2, "default should follow redirects"
    assert httpx_mock.get_requests()[-1].url == url_target_expected

def test_llm_huggingfaceopenai_model_wrapper_disallow_redirects(httpx_mock: HTTPXMock) -> None:
    url_redirect = "https://example.com/redirect"
    url_redirect_expected = "https://example.com/redirect/v1/chat/completions"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    wrapper = get_llm_model_wrapper(
        preset="huggingface-openai",
        api_key="test api key",
        url=url_redirect,
        headers={},
        allow_redirects=False,
    )

    httpx_mock.add_response(
        url=url_redirect_expected, 
        method="POST", 
        status_code=308, 
        headers={"Location":url_target}, 
        json=content_redirect
    )

    with pytest.raises(
        Uncontactable, 
        match=re.escape(_EXPECTED_308_MESSAGE)
    ):
        wrapper("a")

    # we know it's processed the redirect if we got the two requests
    assert len(httpx_mock.get_requests()) == 1, "default should follow redirects"
    assert httpx_mock.get_requests()[-1].url == url_redirect_expected

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_huggingface_openai_model_respects_rate_limits(mock_throttle: mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="huggingface-openai",
        api_key="test api key",
        url="https://example.com/target",
        headers={},
        allow_redirects=False,
        rate_limit=10
    )
    mock_throttle.assert_called_once_with(mock.ANY, rate_limit=10)

    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_azure_openai_model_respects_rate_limits(mock_throttle: mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        model_name="gpt-4o",
        az_api_version="1",
        headers={},
        url="https://example.com/target",
        rate_limit=10
    )
    mock_throttle.assert_called_once_with(mock.ANY, rate_limit=10)

    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_azure_ai_studio_model_respects_rate_limits(mock_throttle: mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="azure-aistudio",
        api_key="test api key",
        model_name="gpt-4o",
        system_prompt="system prompt",
        az_api_version="1",
        headers={},
        url="https://example.com/target",
        rate_limit=10
    )

    mock_throttle.assert_called_with(mock.ANY, rate_limit=10)

    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_openai_model_respects_rate_limits(mock_throttle: mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="openai",
        api_key="test api key",
        model_name="gpt-4o",
        system_prompt="system prompt",
        headers={},
        url="https://example.com/target",
        rate_limit=10
    )

    mock_throttle.assert_called_once_with(mock.ANY, rate_limit=10)

    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value

@mock.patch("mindgard.wrappers.llm.throttle", return_value=mock.MagicMock())
def test_anthropic_model_respects_rate_limits(mock_throttle: mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="anthropic",
        api_key="test api key",
        model_name="claude",
        system_prompt="system prompt",
        headers={},
        url="https://example.com/target",
        rate_limit=10
    )

    mock_throttle.assert_called_once_with(mock.ANY, rate_limit=10)

    ret = wrapper("myprompt", with_context=None)
    mock_throttle.return_value.assert_called_once_with("myprompt", None)
    assert ret == mock_throttle.return_value.return_value


def test_llm_huggingfaceopenai_model_wrapper_default_allow_redirects(httpx_mock: HTTPXMock) -> None:
    url_redirect = "https://example.com/redirect"
    url_redirect_expected = "https://example.com/redirect/v1/chat/completions"
    url_target = "https://example.com/target"
    url_target_expected = url_target
    content_redirect = {"nothing":"here"}

    wrapper = get_llm_model_wrapper(
        preset="huggingface-openai",
        api_key="test api key",
        url=url_redirect,
        headers={},
    )

    httpx_mock.add_response(
        url=url_redirect_expected, 
        method="POST", 
        status_code=308, 
        headers={"Location":url_target}, 
        json=content_redirect
    )
    httpx_mock.add_response(
        url=url_target_expected, 
        method="POST", 
        status_code=200, 
        json=EXAMPLE_CHAT_COMPLETION_RESPONSE
    )

    res = wrapper("a")
    assert res == "my message"

    # we know it's processed the redirect if we got the two requests
    assert len(httpx_mock.get_requests()) == 2, "default should follow redirects"
    assert httpx_mock.get_requests()[-1].url == url_target_expected

def test_llm_openai_compatible_model_wrapper_should_default_to_huggingface_model_name(httpx_mock: HTTPXMock) -> None:
    url_target = "https://example.com/target"

    wrapper = get_llm_model_wrapper(
        preset="openai-compatible",
        api_key="test api key",
        url=url_target,
        headers={},
    )

    httpx_mock.add_response(
        url=url_target + "/v1/chat/completions",
        method="POST",
        status_code=200,
        json=EXAMPLE_CHAT_COMPLETION_RESPONSE
    )

    wrapper("a")

    assert '"model": "tgi"' in str(httpx_mock.get_requests()[0].read())

def test_llm_openai_compatible_model_wrapper_should_allow_overriding_model_name(httpx_mock: HTTPXMock) -> None:
    url_target = "https://example.com/target"

    wrapper = get_llm_model_wrapper(
        preset="openai-compatible",
        api_key="test api key",
        url=url_target,
        model_name="another-model",
        headers={},
    )

    httpx_mock.add_response(
        url=url_target + "/v1/chat/completions",
        method="POST",
        status_code=200,
        json=EXAMPLE_CHAT_COMPLETION_RESPONSE
    )

    wrapper("a")

    assert '"model": "another-model"' in str(httpx_mock.get_requests()[0].read())



def test_llm_azureaistudio_model_wrapper_allow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = {
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "my message",
            },
            "logprobs": None,
            "finish_reason": "stop"
        }]
    }
    wrapper = get_llm_model_wrapper(
        preset="azure-aistudio",
        url=url_redirect,
        api_key="test api key",
        system_prompt="mysysprompt",
        headers={},
        allow_redirects=True,
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})
        m.post(url_target, json=content_target, status_code=200)

        res = wrapper("a")
        assert res == "my message"

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 2, "default should follow redirects"
        assert m.last_request.url == url_target

def test_llm_azureaistudio_model_wrapper_disallow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    wrapper = get_llm_model_wrapper(
        preset="azure-aistudio",
        url=url_redirect,
        api_key="test api key",
        system_prompt="mysysprompt",
        headers={},
        allow_redirects=False,
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})

        with pytest.raises(
            Uncontactable, 
            match=re.escape(_EXPECTED_308_MESSAGE)
        ):
            wrapper("a")
        
        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 1, "should not follow redirects"
        assert m.last_request.url == url_redirect

def test_llm_azureaistudio_model_wrapper_default_allow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = {
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "my message",
            },
            "logprobs": None,
            "finish_reason": "stop"
        }]
    }
    wrapper = get_llm_model_wrapper(
        preset="azure-aistudio",
        url=url_redirect,
        api_key="test api key",
        system_prompt="mysysprompt",
        headers={},
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})
        m.post(url_target, json=content_target, status_code=200)

        res = wrapper("a")
        assert res == "my message"

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 2, "default should follow redirects"
        assert m.last_request.url == url_target


def test_llm_azureopenai_model_wrapper_allow_redirects(httpx_mock: HTTPXMock) -> None:
    url_redirect = "https://example.com/redirect"
    url_redirect_expected = "https://example.com/redirect/openai/deployments/model-name/chat/completions?api-version=a-version"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = {
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "my message",
            },
            "logprobs": None,
            "finish_reason": "stop"
        }],
    }
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        url=url_redirect,
        model_name="model-name",
        az_api_version="a-version",
        headers={},
        allow_redirects=True,
    )

    httpx_mock.add_response(
        url=url_redirect_expected, 
        method="POST", 
        status_code=308, 
        headers={"Location":url_target}, 
        json=content_redirect
    )
    httpx_mock.add_response(
        url=url_target, 
        method="POST", 
        status_code=200, 
        json=content_target
    )

    res = wrapper("a")
    assert res == "my message"

    # we know it's processed the redirect if we got the two requests
    assert len(httpx_mock.get_requests()) == 2, "default should follow redirects"
    assert httpx_mock.get_requests()[-1].url == url_target

def test_llm_azureopenai_model_wrapper_disallow_redirects(httpx_mock: HTTPXMock) -> None:
    url_redirect = "https://example.com/redirect"
    url_redirect_expected = "https://example.com/redirect/openai/deployments/model-name/chat/completions?api-version=a-version"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        url=url_redirect,
        model_name="model-name",
        az_api_version="a-version",
        headers={},
        allow_redirects=False,
    )

    httpx_mock.add_response(
        url=url_redirect_expected, 
        method="POST", 
        status_code=308, 
        headers={"Location":url_target}, 
        json=content_redirect
    )

    with pytest.raises(
        Uncontactable, 
        match=re.escape(_EXPECTED_308_MESSAGE)
    ):
        wrapper("a")

    # we know it's processed the redirect if we got the two requests
    assert len(httpx_mock.get_requests()) == 1, "default should follow redirects"
    assert httpx_mock.get_requests()[-1].url == url_redirect_expected

def test_llm_azureopenai_model_wrapper_unprocessable_entity_exception(httpx_mock: HTTPXMock) -> None:
    url = "https://example.com/redirect"
    url_expected = "https://example.com/redirect/openai/deployments/model-name/chat/completions?api-version=a-version"
    expected_error_detail = "<none>"
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        url=url,
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    httpx_mock.add_response(
        url=url_expected, 
        method="POST", 
        status_code=422,
        text="some garbage"
    )

    with pytest.raises(
        UnprocessableEntity, 
        match=re.escape(f"Received 422 from provider: {expected_error_detail}")
    ):
        wrapper("a")

@mock.patch("mindgard.wrappers.llm.AzureOpenAI", return_value=mock.MagicMock())
def test_llm_azureopenai_model_wrapper_unprocessable_entity_exception_with_message(mock_azureopenai: mock.MagicMock) -> None:

    expected_error_detail = "hello"
    content = {"error":expected_error_detail}
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        url="http://example.com",
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    mock_response = mock.MagicMock(spec=Response)
    mock_response.status_code = 422
    mock_response.headers = {}
    mock_response.json.return_value = content
    mock_azureopenai.return_value.chat.completions.create.side_effect = APIStatusError(
        message="error message",
        response=mock_response,
        body="response body"
    )

    with pytest.raises(
        UnprocessableEntity, 
        match=re.escape(f"Received 422 from provider: {expected_error_detail}")
    ):
        wrapper("a")

@mock.patch("mindgard.wrappers.llm.AzureOpenAI", return_value=mock.MagicMock())
def test_llm_azureopenai_model_wrapper_empty_response_exception(mock_azureopenai:mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        url="https://example.com/redirect",
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    mock_azureopenai.return_value.chat.completions.create.side_effect = OpenAIError("blablabla")

    with pytest.raises(
        EmptyResponse, 
        match=re.escape("An OpenAI error occurred")
    ):
        wrapper("a")


def test_llm_azureopenai_model_wrapper_default_allow_redirects(httpx_mock: HTTPXMock) -> None:
    url_redirect = "https://example.com/redirect"
    url_redirect_expected = "https://example.com/redirect/openai/deployments/model-name/chat/completions?api-version=a-version"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = {
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "my message",
            },
            "logprobs": None,
            "finish_reason": "stop"
        }],
    }
    wrapper = get_llm_model_wrapper(
        preset="azure-openai",
        api_key="test api key",
        url=url_redirect,
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    httpx_mock.add_response(
        url=url_redirect_expected, 
        method="POST", 
        status_code=308, 
        headers={"Location":url_target}, 
        json=content_redirect
    )
    httpx_mock.add_response(
        url=url_target, 
        method="POST", 
        status_code=200, 
        json=content_target
    )

    res = wrapper("a")
    assert res == "my message"

    # we know it's processed the redirect if we got the two requests
    assert len(httpx_mock.get_requests()) == 2, "default should follow redirects"
    assert httpx_mock.get_requests()[-1].url == url_target


def test_llm_huggingface_model_wrapper_allow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = [{"generated_text":"my message"}]
    wrapper = get_llm_model_wrapper(
        preset="huggingface",
        url=url_redirect,
        api_key="test api key",
        request_template='{"something":"{prompt}{system_prompt}"}',
        headers={},
        allow_redirects=True,
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})
        m.post(url_target, json=content_target, status_code=200)

        res = wrapper("a")
        assert res == "my message"

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 2, "default should follow redirects"
        assert m.last_request.url == url_target

def test_llm_huggingface_model_wrapper_disallow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    wrapper = get_llm_model_wrapper(
        preset="huggingface",
        url=url_redirect,
        api_key="test api key",
        request_template='{"something":"{prompt}{system_prompt}"}',
        headers={},
        allow_redirects=False,
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})

        with pytest.raises(
            Uncontactable, 
            match=re.escape(_EXPECTED_308_MESSAGE)
        ):
            wrapper("a")

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 1, "should not follow redirects"
        assert m.last_request.url == url_redirect

def test_llm_huggingface_model_wrapper_default_allow_redirects() -> None:
    url_redirect = "https://example.com/redirect"
    url_target = "https://example.com/target"
    content_redirect = {"nothing":"here"}
    content_target = [{"generated_text":"my message"}]
    wrapper = get_llm_model_wrapper(
        preset="huggingface",
        url=url_redirect,
        api_key="test api key",
        request_template='{"something":"{prompt}{system_prompt}"}',
        headers={},
    )

    with requests_mock.mock() as m:
        m.post(url_redirect, json=content_redirect, status_code=308, headers={"Location":url_target})
        m.post(url_target, json=content_target, status_code=200)

        res = wrapper("a")
        assert res == "my message"

        # we know it's processed the redirect if we got the two requests
        assert len(m.request_history) == 2, "default should follow redirects"
        assert m.last_request.url == url_target


def test_llm_openai_model_wrapper_unprocessable_entity_exception(httpx_mock: HTTPXMock) -> None:
    url_expected = "https://api.openai.com/v1/chat/completions"
    expected_error_detail = "<none>"
    wrapper = get_llm_model_wrapper(
        preset="openai",
        api_key="test api key",
        model_name="model-name",
        headers={},
    )

    httpx_mock.add_response(
        url=url_expected, 
        method="POST", 
        status_code=422,
        text="some garbage"
    )

    with pytest.raises(
        UnprocessableEntity, 
        match=re.escape(f"Received 422 from provider: {expected_error_detail}")
    ):
        wrapper("a")

@mock.patch("mindgard.wrappers.llm.OpenAI", return_value=mock.MagicMock())
def test_llm_openai_model_wrapper_unprocessable_entity_exception_with_message(mock_azureopenai: mock.MagicMock) -> None:

    expected_error_detail = "hello"
    content = {"error":expected_error_detail}
    wrapper = get_llm_model_wrapper(
        preset="openai",
        api_key="test api key",
        url="http://example.com",
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    mock_response = mock.MagicMock(spec=Response)
    mock_response.status_code = 422
    mock_response.headers = {}
    mock_response.json.return_value = content
    mock_azureopenai.return_value.chat.completions.create.side_effect = APIStatusError(
        message="error message",
        response=mock_response,
        body="response body"
    )

    with pytest.raises(
        UnprocessableEntity, 
        match=re.escape(f"Received 422 from provider: {expected_error_detail}")
    ):
        wrapper("a")

@mock.patch("mindgard.wrappers.llm.OpenAI", return_value=mock.MagicMock())
def test_llm_openai_model_wrapper_empty_response_exception(mock_azureopenai:mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="openai",
        api_key="test api key",
        url="https://example.com/redirect",
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    mock_azureopenai.return_value.chat.completions.create.side_effect = OpenAIError("blablabla")

    with pytest.raises(
        EmptyResponse, 
        match=re.escape("An OpenAI error occurred")
    ):
        wrapper("a")


@mock.patch("mindgard.wrappers.llm.OpenAI", return_value=mock.MagicMock())
def test_llm_openai_model_wrapper_raises_unauthorized_errors(mock_azureopenai:mock.MagicMock) -> None:
    wrapper = get_llm_model_wrapper(
        preset="openai",
        api_key="test api key",
        url="https://example.com/redirect",
        model_name="model-name",
        az_api_version="a-version",
        headers={},
    )

    mock_azureopenai.return_value.chat.completions.create.side_effect = AuthenticationError(message="_",
                                                                                            response=httpx.Response(
                                                                                                status_code=401,
                                                                                                request=MagicMock()),
                                                                                            body=None)

    with pytest.raises(
        Unauthorized,
        match=re.escape("Failed to contact model: model returned a 401 (unauthorized).")
    ):
        wrapper("a")


def test_llm_custom_model_wrapper_exception_of_unknown_status() -> None:
    status_code = 455
    url = "https://blah.com/model"
    expected_error_detail = "An unexpected error occurred:<Response [455]>"

    with requests_mock.Mocker() as m:
        m.post(url, status_code=status_code)

        wrapper = APIModelWrapper(
            url,
            system_prompt="mysysprompt",
            rate_limit=100
        )

        with pytest.raises(
                HTTPBaseError,
                match=re.escape(expected_error_detail),
        ):
            wrapper("a")
