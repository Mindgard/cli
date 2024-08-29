import requests_mock
import base64
import pytest

from mindgard.wrappers.image import ImageModelWrapper, LabelConfidence
from mindgard.wrappers.llm import TestStaticResponder, ContextManager, APIModelWrapper

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


def test_image_model_wrapper_aligns_responses() -> None:
    url = "https://example.com/somewhere"
    wrapper = ImageModelWrapper(
        url=url,
        labels=["0","1"],
        api_key="test api key"
    )

    with requests_mock.mock() as m:
        image=base64.b64encode("hello world".encode("utf-8"))
        mock = m.post(
            url,
            json=[{"label":"1","score":"0.2"},{"label":"0","score":"0.1"}],
        )
        assert wrapper(image) == [LabelConfidence(label="0",score="0.1"),LabelConfidence(label="1",score="0.2")]
        assert mock.last_request.headers["Accept"] == "application/json"
        assert mock.last_request.headers["Content-Type"] == "image/jpeg"
        assert mock.last_request.headers["Authorization"] == "Bearer test api key"
        assert mock.last_request.text == image.decode("utf-8")

def test_image_model_wrapper_missing_labels_raises_valueerror() -> None:
    url = "https://example.com/somewhere"
    wrapper = ImageModelWrapper(
        url=url,
        labels=["0"],
        api_key="test api key"
    )

    with requests_mock.mock() as m:
        image=base64.b64encode("hello world".encode("utf-8"))
        mock = m.post(
            url,
            json=[{"label":"1","score":"0.2"},{"label":"0","score":"0.1"}],
        )
        with pytest.raises(ValueError):
            wrapper(image)
        assert mock.last_request.text == image.decode("utf-8")
        assert mock.last_request.headers["Accept"] == "application/json"
        assert mock.last_request.headers["Content-Type"] == "image/jpeg"
        assert mock.last_request.headers["Authorization"] == "Bearer test api key"