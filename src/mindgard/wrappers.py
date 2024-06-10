from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, cast
from anthropic import Anthropic
from anthropic.types import MessageParam
from .error import ExpectedError, NoOpenAIResponseError
import requests
from openai import AzureOpenAI, OpenAI
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
        system_prompt: Optional[str] = None,
        tokenizer: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        self.context_manager = ContextManager()
        self.api_url = api_url
        if tokenizer:
            logging.debug("Note that with tokenizer enabled, the request_template format is different.")
            self.request_template =  request_template or '{"prompt": "{tokenized_chat_template}"}'
            if '{tokenized_chat_template}' not in self.request_template:
                raise ExpectedError("`--request-template` must contain '{tokenized_chat_template}' when using a tokenizer.")
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer)
        else:
            self.tokenizer = None
            default_template = '{"prompt": "{system_prompt}{prompt}"}' if system_prompt is None else '{"prompt": "{system_prompt} {prompt}"}'
            self.request_template = request_template or default_template
            if '{prompt}' not in self.request_template or '{system_prompt}' not in self.request_template:
                raise ExpectedError("`--request-template` must contain '{prompt}' and '{system_prompt}'.")
        self.selector = selector
        self.system_prompt = system_prompt or ""
        self.headers = headers or {}


    def prompt_to_request_payload(self, prompt: str) -> Dict[str, Any]:
        if self.tokenizer:
            tokenized_chat_template = cast(str, self.tokenizer.apply_chat_template([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ], tokenize=False))

            tokenized_chat_template = json.dumps(tokenized_chat_template, ensure_ascii=False)
            payload = self.request_template.replace("{tokenized_chat_template}", tokenized_chat_template)
        else:
            # Dump to escape quote marks that are inside the prompt/system_prompt
            prompt = json.dumps(prompt, ensure_ascii=False)
            system_prompt = json.dumps(self.system_prompt, ensure_ascii=False)
            # The dumps added extra quote marks to prompt and system prompt so trim them before the replace
            payload = self.request_template.replace("{prompt}", prompt[1:-1])
            payload = payload.replace("{system_prompt}", system_prompt[1:-1])

        logging.debug(f"{payload=}")
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
        try:
            response = requests.post(self.api_url, headers=self.headers, json=request_payload)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as cerr:
            # this means the endpoint was uncontactable
            raise cerr
        except requests.exceptions.HTTPError as httperr:
            # this means the endpoint didn't like how we were acting, i.e check status code
            raise httperr
        except Exception as e:
            # everything else
            raise e

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


class AzureAIStudioWrapper(APIModelWrapper):
    def __init__(self, api_key: str, url: str, request_template: Optional[str], system_prompt: str) -> None:
        az_request_template = request_template or """{
    "messages": [
        {"role": "system", "content": "{system_prompt}"},
        {"role": "user", "content": "{prompt}"}
    ],
    "temperature": 0.2,
    "max_tokens": 1024,
    "stop": [],
    "top_p": 0.9
}"""
        super().__init__(
            url,
            request_template=az_request_template,
            selector='["choices"][0]["message"]["content"]',
            headers={"Authorization": f'Bearer {api_key}', "Content-Type": "application/json"},
            system_prompt=system_prompt
        )
    
    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        if with_context is not None:
            logging.debug("APIModelWrapper is temporarily incompatible with chat completions history. Attacks that require chat completions history fail.")
            raise NotImplementedError("The crescendo attack is currently incompatible with custom model wrappers.")

        request_payload = self.prompt_to_request_payload(content)

        # Make the API call
        response = requests.post(self.api_url, headers=self.headers, json=request_payload)
        if response.status_code == 400:
            try:
                # Detect Azure Content Filter error message
                err_res_json = response.json()
                if err_message := err_res_json.get("error", {}).get("message", None):
                    return cast(str, err_message)
            except Exception as e:
                raise Exception(f"API call failed with {response.status_code=} {response.json()=}. Attempt to decode response failed with {e=}")
        elif response.status_code != 200:
            # Handle other types of API error
            raise Exception(f"API call failed with {response.status_code=} {response.json()=}.")

        res_json: Dict[str, Any] = cast(Dict[str, Any], response.json())

        # Detect Cohere content_filter error
        if res_json["choices"][0]["finish_reason"] == "content_filter":
            return "Sorry, but a content filter was triggered. Please try again with a different prompt."
        
        # Now we are sure that the response was successful and not a content filter error
        if self.selector:
            jsonpath_expr = jsonpath_ng.parse(self.selector)
            match = jsonpath_expr.find(res_json)
            if match:
                return match[0].value
            else:
                raise Exception(f"Selector {self.selector} did not match any elements in the response. {res_json=}")

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


# https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#chat-completions to see available values for az_api_version
# ["2023-05-15", "2023-06-01-preview", "2023-10-01-preview", "2024-02-15-preview", "2024-03-01-preview", "2024-04-01-preview", "2024-02-01"] on May 15th 2024
class AzureOpenAIWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: str, az_api_version: str, url: str, system_prompt: Optional[str] = None) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.client = AzureOpenAI(api_key=api_key, api_version=az_api_version, azure_endpoint=url)
        self.system_prompt = system_prompt

    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        return openai_call(wrapper=self, content=content, with_context=with_context)


class OpenAIWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: Optional[str], system_prompt: Optional[str] = None) -> None:
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name or "gpt-3.5-turbo"
        self.system_prompt = system_prompt

    def __call__(self, content:str, with_context:Optional[Context] = None) -> str:
        return openai_call(wrapper=self, content=content, with_context=with_context)


def openai_call(wrapper: Union[AzureOpenAIWrapper, OpenAIWrapper], content:str, with_context:Optional[Context] = None) -> str:
    if wrapper.system_prompt:
        messages = [{"role": "system", "content": wrapper.system_prompt}]
    else:
        messages = []

    if with_context:
        for prompt_response in with_context.turns:
            messages.append({"role":"user","content": prompt_response.prompt})
            messages.append({"role":"assistant","content": prompt_response.response})
    
    messages.append({"role":"user", "content":content})

    chat = wrapper.client.chat.completions.create(model=wrapper.model_name, messages=messages)  # type: ignore # TODO: fix type error
    response = chat.choices[0].message.content

    if not response:
        raise NoOpenAIResponseError("No response from OpenAI.")

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
    

    

def check_expected_args(args: Dict[str, Any], expected_args: List[str]) -> None:
    missing_args: List[str] = []
    for arg in expected_args:
        if not args.get(arg):
            missing_args.append(f"`--{arg.replace('_', '-')}`")
    if missing_args:
        raise ExpectedError(f"Missing required arguments: {', '.join(missing_args)}")


def get_model_wrapper(
    headers_string: Optional[str],
    preset: Optional[Literal['huggingface', 'openai', 'azure-openai', 'azure-aistudio', 'anthropic', 'tester']] = None,
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    model_name: Optional[str] = None,
    az_api_version: Optional[str] = None,
    system_prompt: Optional[str] = None,
    selector: Optional[str] = None,
    request_template: Optional[str] = None,
    tokenizer: Optional[str] = None
) -> ModelWrapper:

    # Create model based on preset
    if preset == 'huggingface':
        check_expected_args(locals(), ['api_key', 'url', 'request_template'])
        api_key, url, request_template = cast(Tuple[str, str, str], (api_key, url, request_template))
        return HuggingFaceWrapper(api_key=api_key, api_url=url, system_prompt=system_prompt, request_template=request_template)
    elif preset == 'azure-aistudio':
        check_expected_args(locals(), ['api_key', 'url', 'system_prompt'])
        api_key, url, system_prompt = cast(Tuple[str, str, str], (api_key, url, system_prompt))
        return AzureAIStudioWrapper(api_key=api_key, url=url, request_template=request_template, system_prompt=system_prompt)
    elif preset == 'openai':
        check_expected_args(locals(), ['api_key'])
        api_key = cast(str, api_key)
        return OpenAIWrapper(api_key=api_key, model_name=model_name, system_prompt=system_prompt)
    elif preset == 'azure-openai':
        check_expected_args(locals(), ['api_key', 'model_name', 'az_api_version', 'url'])
        api_key, model_name, az_api_version, url = cast(Tuple[str, str, str, str], (api_key, model_name, az_api_version, url))
        return AzureOpenAIWrapper(api_key=api_key, model_name=model_name, az_api_version=az_api_version, url=url, system_prompt=system_prompt)
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
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, system_prompt=system_prompt, tokenizer=tokenizer, headers=headers)
        else:
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, system_prompt=system_prompt, tokenizer=tokenizer)


def parse_args_into_model(args: Dict[str, Any]) -> ModelWrapper:
    return get_model_wrapper(
        preset=args["preset"],
        headers_string=args["headers"],
        api_key=args["api_key"],
        url=args["url"],
        selector=args["selector"],
        request_template=args["request_template"],
        system_prompt=args["system_prompt"],
        model_name=args["model_name"],
        az_api_version=args["az_api_version"],
        tokenizer=args["tokenizer"],
    )