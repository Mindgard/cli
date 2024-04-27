from abc import ABC, abstractmethod
import json
from typing import Any, List, Literal, Optional, cast
from anthropic import Anthropic
from anthropic.types import MessageParam
from .error import ExpectedError
import requests
from openai import OpenAI
import jsonpath_ng
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

class ModelWrapper(ABC):
    @abstractmethod
    def __call__(self, prompt: str) -> str:
        pass


class TestStaticResponder(ModelWrapper):
    """
    This is only for testing
    """
    def __init__(self):
        pass
    
    def __call__(self, prompt: str) -> str:
        short_prompt = prompt[0:40]
        return f"I'm a static responder; prompted with (limit 40): {short_prompt}"

class WebModelWrapper(ModelWrapper):
    def __init__(
            self,
            url: str,
            input_selector: str,
            submit_selector: str,
            output_selector: str,
            ready_selector: str
    ) -> None:
        self.driver = webdriver.Chrome()
        self.url = url
        self.input_selector = input_selector
        self.submit_selector = submit_selector
        self.output_selector = output_selector
        self.ready_selector = ready_selector


    def wait_for_element(self, selector: str):
        return WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

    def __call__(self, prompt: str) -> str:
        try:
            browser = self.driver
            browser.get(self.url)
            browser.set_window_size(1000,900)

            self.wait_for_element(self.ready_selector).click()

            JS_ADD_TEXT_TO_INPUT = """
              var elm = arguments[0], txt = arguments[1];
              elm.value += txt;
              elm.dispatchEvent(new Event('change'));
              """

            time.sleep(1)

            input = self.wait_for_element(self.input_selector)

            browser.execute_script(JS_ADD_TEXT_TO_INPUT, input, prompt)
            input.send_keys(' ')

            self.wait_for_element(self.submit_selector).click()

            time.sleep(1)

            self.wait_for_element(self.input_selector)

            response = browser.find_elements(By.CSS_SELECTOR, self.output_selector)[-1].text

            return response
        except Exception:
            return ''


class APIModelWrapper(ModelWrapper):
    def __init__(
        self,
        api_url: str,
        request_template: Optional[str] = None,
        selector: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        system_prompt: Optional[str] = None
    ) -> None:
        # TODO: do we want to default to a system_prompt
        self.system_prompt = system_prompt or ""
        self.selector = selector
        self.headers = headers or {}
        self.api_url = api_url
        self.request_template = request_template or '{"prompt": "{system_prompt} {prompt}"}'

        if '{prompt}' not in self.request_template or '{system_prompt}' not in self.request_template:
            raise ExpectedError("`--request-template` must contain '{prompt}' and '{system_prompt}'.")

    def prompt_to_request_payload(self, prompt: str) -> dict[str, Any]:
        # Dump to escape quote marks that are inside the prompt/system_prompt
        prompt = json.dumps(prompt, ensure_ascii=False)
        system_prompt = json.dumps(self.system_prompt, ensure_ascii=False)

        # The dumps added extra quote marks to prompt and system prompt so trim them before the replace
        payload = self.request_template.replace("{prompt}", prompt[1:-1])
        payload = payload.replace("{system_prompt}", system_prompt[1:-1])

        # should handle non-json payload (or single string)
        payload = json.loads(payload)
        return payload

    def __call__(self, prompt: str) -> str:
        request_payload = self.prompt_to_request_payload(prompt)

        # Make the API call
        response = requests.post(self.api_url, headers=self.headers, json=request_payload)
        # print(response.text)
        if response.status_code != 200:
            raise Exception(f"API call failed with status code {response.status_code}")

        response = response.json()

        if self.selector:
            jsonpath_expr = jsonpath_ng.parse(self.selector)
            match = jsonpath_expr.find(response)
            if match:
                return match[0].value
            else:
                raise Exception(f"Selector {self.selector} did not match any elements in the response. {response=}")

        return response


class HuggingFaceWrapper(APIModelWrapper):
    def __init__(self, api_key: str, api_url: str, request_template: str, system_prompt: Optional[str] = None) -> None:
        super().__init__(
            api_url,
            request_template=request_template,
            selector='[0]["generated_text"]',
            headers={'Authorization': f'Bearer {api_key}'},
            system_prompt=system_prompt
        )


class OpenAIWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: Optional[str], system_prompt: Optional[str] = None) -> None:
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name or "gpt-3.5-turbo"
        self.system_prompt = system_prompt

    def __call__(self, prompt: str) -> str:
        if self.system_prompt:
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}]
        else:
            messages = [{"role": "user", "content": prompt}]

        chat = self.client.chat.completions.create(model=self.model_name, messages=messages)  # type: ignore # TODO: fix type error
        response = chat.choices[0].message.content

        if not response:
            raise ExpectedError("No response from OpenAI.")

        return response


class AnthropicWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: Optional[str], system_prompt: Optional[str] = None) -> None:
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name or "claude-3-opus-20240229"
        self.system_prompt = system_prompt

    def __call__(self, prompt: str) -> str:
        messages: List[MessageParam]
        if self.system_prompt:
            messages = [{"role": "assistant", "content": self.system_prompt}, {"role": "user", "content": prompt}]
        else:
            messages = [{"role": "user", "content": prompt}]
        message = self.client.messages.create(max_tokens=1024, messages=messages, model=self.model_name)
        response = message.content[0].text

        return response


def get_model_wrapper(
    headers_string: Optional[str],
    preset: Optional[Literal['huggingface', 'openai', 'anthropic', 'tester']] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    model_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    selector: Optional[str] = None,
    request_template: Optional[str] = None
) -> ModelWrapper:

    # Create model based on preset
    if preset == 'huggingface':
        missing_args: List[str] = []
        if not api_key:
            missing_args.append("`--api-key`")
        if not url:
            missing_args.append("`--url`")
        if not request_template:
            missing_args.append("`--request-template`")
        if missing_args:
            raise ExpectedError(f"Missing required arguments: {', '.join(missing_args)}")
        api_key = cast(str, api_key)
        url = cast(str, url)
        request_template = cast(str, request_template)
        return HuggingFaceWrapper(api_key=api_key, api_url=url, system_prompt=system_prompt, request_template=request_template)
    elif preset == 'openai':
        if not api_key:
            raise ExpectedError("`--api-key` argument is required when using the 'openai' preset.")
        return OpenAIWrapper(api_key=api_key, model_name=model_name, system_prompt=system_prompt)
    elif preset == 'anthropic':
        if not api_key:
            raise ExpectedError("`--api-key` argument is required when using the 'anthropic' preset.")
        return AnthropicWrapper(api_key=api_key, model_name=model_name, system_prompt=system_prompt)
    elif preset == 'tester':
        return TestStaticResponder()
    else:
        if not url:
            raise ExpectedError("`--url` argument is required when not using a preset configuration.")
        # Convert headers string to dictionary
        if headers_string:
            headers = dict(item.split(": ") for item in headers_string.split(", "))
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, headers=headers, system_prompt=system_prompt)
        else:
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, system_prompt=system_prompt)
