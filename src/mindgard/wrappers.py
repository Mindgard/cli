from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, List, Literal, Optional, cast
from anthropic import Anthropic
from anthropic.types import MessageParam
from .error import ExpectedError
import requests
from openai import OpenAI
import jsonpath_ng


@dataclass
class PromptResponse:
    prompt:str
    response:str

class Context:
    def __init__(self) -> None:
        self.turns:list[PromptResponse] = []

    def add(self, prompt_response:PromptResponse) -> None:
        self.turns.append(prompt_response)

class ContextManager:
    def __init__(self) -> None:
        self.contexts:Dict[str,Context] = {}

    def get_context_or_none(self, context_id:Optional[str] = None) -> Optional[Context]:
        if context_id is None:
            return None
        if self.contexts.get(context_id, None) is None:
            self.contexts[context_id] = Context()
        return self.contexts[context_id]

class ModelWrapper(ABC):
    @abstractmethod
    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        pass

class TestStaticResponder(ModelWrapper):
    """
    This is only for testing
    """
    def __init__(self, system_prompt: str):
        self.context_manager = ContextManager()
        self._system_prompt = system_prompt
        pass
    
    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        request = f"[start]sys: {self._system_prompt};"
        if with_context is not None:
            request = f"{request}"
            for prompt_response in with_context.turns:
                request = f"{request} user: {prompt_response.prompt}; assistant: {prompt_response.response};"
            request = f"{request}"
        else:
            request = f"{request}"
        request = f"{request} next: {content}[end]"

        response = f"TEST. prompted with: {request=}"

        if with_context is not None:
            with_context.add(PromptResponse(
                prompt=content,
                response=response
            ))
        return response

class APIModelWrapper(ModelWrapper):
    def __init__(
        self,
        api_url: str,
        request_template: Optional[str] = None,
        selector: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        system_prompt: Optional[str] = None
    ) -> None:
        self.context_manager = ContextManager()
        self.system_prompt = system_prompt or ""
        self.selector = selector
        self.headers = headers or {}
        self.api_url = api_url
        default_template = '{"prompt": "{system_prompt}{prompt}"}' if system_prompt is None else '{"prompt": "{system_prompt} {prompt}"}'
        self.request_template = request_template or default_template

        if '{prompt}' not in self.request_template or '{system_prompt}' not in self.request_template:
            raise ExpectedError("`--request-template` must contain '{prompt}' and '{system_prompt}'.")

    def prompt_to_request_payload(self, prompt: str) -> Dict[str, Any]:
        # Dump to escape quote marks that are inside the prompt/system_prompt
        prompt = json.dumps(prompt, ensure_ascii=False)
        system_prompt = json.dumps(self.system_prompt, ensure_ascii=False)

        # The dumps added extra quote marks to prompt and system prompt so trim them before the replace
        payload = self.request_template.replace("{prompt}", prompt[1:-1])
        payload = payload.replace("{system_prompt}", system_prompt[1:-1])

        # should handle non-json payload (or single string)
        payload = json.loads(payload)
        assert isinstance(payload, dict), f"Expected the request template to form a json dict, got {type(payload)} instead."
        return cast(Dict[str, Any], payload)


    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        if with_context is not None:
            logging.debug("APIModelWrapper is temporarily incompatible with chat completions history. Attacks that require chat completions history fail.")
            raise NotImplementedError("The crescendo attack is currently incompatible with custom model wrappers.")

        request_payload = self.prompt_to_request_payload(content)

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

        # disabled until we can support templating chat completions
        # if with_context is not None:
        #     with_context.add(PromptResponse(
        #         prompt=content,
        #         response=response
        #     ))

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

    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        if self.system_prompt:
            messages = [{"role": "system", "content": self.system_prompt}]
        else:
            messages = []

        if with_context:
            for prompt_response in with_context.turns:
                messages.append({"role":"user","content": prompt_response.prompt})
                messages.append({"role":"assistant","content": prompt_response.response})
        
        messages.append({"role":"user", "content":content})

        chat = self.client.chat.completions.create(model=self.model_name, messages=messages)  # type: ignore # TODO: fix type error
        response = chat.choices[0].message.content

        if not response:
            raise ExpectedError("No response from OpenAI.")

        if with_context is not None:
            with_context.add(PromptResponse(
                prompt=content,
                response=response,
            ))
        return response


class AnthropicWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: Optional[str], system_prompt: Optional[str] = None) -> None:
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name or "claude-3-opus-20240229"
        self.system_prompt = system_prompt

    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        messages: List[MessageParam] = []

        messages = []
        if with_context:
            for prompt_response in with_context.turns:
                messages.append({"role":"user","content": prompt_response.prompt})
                messages.append({"role":"assistant","content": prompt_response.response})

        messages.append({"role":"user", "content":content})

        if self.system_prompt is not None:
            message = self.client.messages.create(
                system=self.system_prompt,
                max_tokens=1024, 
                messages=messages, 
                model=self.model_name
            )
        else:
            message = self.client.messages.create(
                max_tokens=1024, 
                messages=messages, 
                model=self.model_name
            )
        response = message.content[0].text

        if with_context is not None:
            with_context.add(PromptResponse(
                prompt=content,
                response=response,
            ))
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
        if not system_prompt:
            raise ExpectedError("`--system-prompt` argument is required")
        return TestStaticResponder(system_prompt=system_prompt)
    else:
        if not url:
            raise ExpectedError("`--url` argument is required when not using a preset configuration.")
        # Convert headers string to dictionary
        if headers_string:
            headers: Dict[str, str] = {}
            for key_and_value_str in headers_string.split(","):
                key, value = key_and_value_str.strip().split(":")
                headers[key.strip()] = value.strip()
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, headers=headers, system_prompt=system_prompt)
        else:
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, system_prompt=system_prompt)
