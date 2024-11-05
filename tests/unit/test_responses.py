import requests_mock
import json
from mindgard.responses import extract_reply, extract_replies
from pytest import fail
from unittest.mock import Mock
from requests import Response

def test_extract_replies_should_extract_selector_match_with_single_result() -> None:
    input = '{"hello": "world"}'
    def returns_input():
        return json.loads(input)

    response = Mock(spec=Response)
    response.headers = {}
    response.json = returns_input

    assert "world" == extract_replies(response, selector="$.hello")

def test_extract_replies_should_extract_selector_match_with_text_stream() -> None:
    input = [
        'data: {"message": "hello"}'.encode("utf-8"),
        'data: {"message": "world"}'.encode("utf-8")
    ]
    def iter_lines():
        return input

    response = Mock(spec=Response)
    response.headers = {"Content-Type": "text/event-stream"}
    response.iter_lines = iter_lines

    assert "hello world" == extract_replies(response, selector="$.message")


def test_extract_replies_should_extract_selector_match_with_text_stream() -> None:
    input = [
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.362203Z","message":{"role":"assistant","content":"Black"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.389563Z","message":{"role":"assistant","content":","},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.417311Z","message":{"role":"assistant","content":" with"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.445099Z","message":{"role":"assistant","content":" some"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.472483Z","message":{"role":"assistant","content":" twink"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.499488Z","message":{"role":"assistant","content":"ling"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.526053Z","message":{"role":"assistant","content":" stars"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.55277Z","message":{"role":"assistant","content":"!"},"done":false}'.encode("utf-8"),
        '{"model":"llama3.2","created_at":"2024-11-04T15:28:14.579312Z","message":{"role":"assistant","content":""},"done_reason":"stop","done":true,"total_duration":434427250,"load_duration":29353875,"prompt_eval_count":44,"prompt_eval_duration":185878000,"eval_count":9,"eval_duration":217092000}'.encode("utf-8"),
    ]
    def iter_lines():
        return input

    response = Mock(spec=Response)
    response.headers = {"Content-Type": "application/x-ndjson"}
    response.iter_lines = iter_lines

    assert "Black, with some twinkling stars!" == extract_replies(response, selector="$.message.content")

def test_extract_replies_should_trim_extraneous_whitespace() -> None:
    input = [
        'data: {"message": "hello "}'.encode("utf-8"),
        'data: {"message": "  world"}'.encode("utf-8")
    ]
    def iter_lines():
        return input

    response = Mock(spec=Response)
    response.headers = {"Content-Type": "text/event-stream"}
    response.iter_lines = iter_lines

    assert "hello world" == extract_replies(response, selector="$.message")

def test_extract_replies_should_ignore_empty_lines() -> None:
    input = [
        'data: {"message": "hello"}'.encode("utf-8"),
        ''.encode("utf-8"),
        'data: {}'.encode("utf-8"),
        'data: {"message": "world"}'.encode("utf-8")
    ]
    def iter_lines():
        return input

    response = Mock(spec=Response)
    response.headers = {"Content-Type": "text/event-stream"}
    response.iter_lines = iter_lines

    assert "hello world" == extract_replies(response, selector="$.message")

def test_extract_replies_should_tolerate_selector_mismatches() -> None:
    input = [
        'data: {"message": "hello"}'.encode("utf-8"),
        ''.encode("utf-8"),
        'data: {"another":"message","type":"ignore"}'.encode("utf-8"),
        'data: {"message": "world"}'.encode("utf-8")
    ]
    def iter_lines():
        return input

    response = Mock(spec=Response)
    response.headers = {"Content-Type": "text/Event-Stream"}
    response.iter_lines = iter_lines

    assert "hello world" == extract_replies(response, selector="$.message")

def test_extract_reply_should_return_input_as_string_when_no_selector() -> None:
    input = '{"hello": "world"}'

    assert input == extract_reply(json.loads(input))

def test_extract_reply_should_return_empty_string_when_no_selector_match_in_non_strict_mode() -> None:
    input = '{"hello": "world"}'

    assert "" == extract_reply(json.loads(input), selector="$.greeting", strict=False)

def test_extract_reply_should_throw_when_no_selector_match_in_non_strict_mode() -> None:
    input = '{"hello": "world"}'

    try:
        extract_reply(json.loads(input), selector="$.greeting", strict=True)
        fail("should have thrown due to selector mismatch")
    except:
        print("threw expected exception")

def test_extract_reply_should_extract_selector_match() -> None:
    input = '{"hello": "world"}'

    assert "world" == extract_reply(json.loads(input), selector="$.hello")