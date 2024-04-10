from abc import ABC, abstractmethod
import json
from typing import Any, List, Literal, Optional
from anthropic import Anthropic
from anthropic.types import MessageParam
import requests
from openai import OpenAI
import jsonpath_ng

from .template import Template

class ModelWrapper(ABC):
    @abstractmethod
    def __call__(self, prompt: str) -> str:
        pass

class APIModelWrapper(ModelWrapper):
    def __init__(self, api_url: str, request_template: Optional[str] = None, selector: Optional[str] = None, headers: Optional[dict[str, str]] = None, system_prompt: Optional[str] = None) -> None:
        # TODO: do we want to default to a system_prompt
        self.system_prompt = system_prompt or ""
        self.selector = selector
        self.headers = headers or {}
        self.api_url = api_url
        self.request_template = request_template or "{system_prompt} {prompt}".strip()

        if '{prompt}' not in self.request_template or '{system_prompt}' not in self.request_template:
            raise Exception("Request template must contain '{prompt}' and '{system_prompt}'.")
    
    def prompt_to_request_payload(self, prompt: str) -> dict[str, Any]:
        # Dump to escape quote marks that are inside the prompt/system_prompt
        prompt = json.dumps(prompt)
        system_prompt = json.dumps(self.system_prompt)

        # The dumps added extra quote marks to prompt and system prompt so trim them before the replace
        payload = self.request_template.replace("{prompt}", prompt[1:-1])
        payload = payload.replace("{system_prompt}", system_prompt[1:-1])

        payload = json.loads(payload)
        return payload

    def __call__(self, prompt: str) -> str:
        request_payload = self.prompt_to_request_payload(prompt)

        # Make the API call
        # import time
        # time.sleep(0.5)
        # return "I can't assist with that."
        response = requests.post(self.api_url, headers=self.headers, json=request_payload)

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

# MindgardMistralExample(
#     api_url=GPU-A100-URL/infer,
#     request_template='{"prompt": "[INST] {system_prompt} {prompt} [/INST]"}'
#     selector='["response"]',
#     headers=None,
#     system_prompt="""You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.\n"""
# ) -> None:
# $ mindgard attack devmodev2 --url GPU-A100-URL/infer --selector '["response"]' --request_template '{"prompt": "[INST] {system_prompt} {prompt} [/INST]"}' --system_prompt test


class HuggingFaceWrapper(APIModelWrapper):
    def __init__(self, api_key: str, api_url: str, system_prompt: Optional[str] = None) -> None:
        super().__init__(
            api_url, 
            request_template='{"prompt": "[INST] {system_prompt} {prompt} [/INST]"}', 
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

        chat = self.client.chat.completions.create(model=self.model_name, messages=messages) # type: ignore # TODO: fix type error
        response = chat.choices[0].message.content 

        if not response:
            raise Exception("No response from OpenAI")

        return response

# Not functioning but an idea of how you would reimplement the OpenAIWrapper in a raw way (not using sdk)
# class OpenAIHTTPWrapper(APIModelWrapper):
#     def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo", template: Optional[Template] = None) -> None:
#         super().__init__(
#             api_url="https://api.openai.com/v1/chat/completions", 
#             request_template='{"messages": [{"role": "system", "content": <{SYSTEM_PROMPT}>}, {"role": "user", "content": "<{PROMPT}>"}], "model": "gpt-3.5-turbo", "temperature": 0.0, "max_tokens": 1024}', 
#             selector='choices[0].message.content', 
#             headers={'Authorization': f'Bearer {api_key}'}, template=template
#         )


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
    
def get_wrapper(preset: Literal['huggingface', 'openai', 'anthropic'], system_prompt=None, api_key=None, url=None, model_name=None):
    if system_prompt:
        llm_template = Template(system_prompt_file="Test")

    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url, template=llm_template)
    elif preset == 'openai':
        model = OpenAIWrapper(api_key=api_key, system_prompt=system_prompt, model_name=model_name)
    elif preset == 'anthropic':
        model = AnthropicWrapper(api_key=api_key, model_name=model_name)
    
    return model


def get_model_wrapper(
    headers_string: Optional[str], 
    preset: Optional[Literal['huggingface', 'openai', 'anthropic']] = None, 
    api_key: Optional[str] = None, 
    url: Optional[str] = None, 
    model_name: Optional[str] = None, 
    system_prompt: Optional[str] = None, 
    selector=None, 
    request_template=None
) -> ModelWrapper:
    # llm template
    llm_template = Template(system_prompt_file="Test")

    # Create model based on preset
    if preset == 'huggingface':
        return HuggingFaceWrapper(api_key=api_key, api_url=url, template=llm_template)
    elif preset == 'openai':
        return OpenAIWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'anthropic':
        return AnthropicWrapper(api_key=api_key, model_name=model_name)
    else:
        # Convert headers string to dictionary
        if headers_string:
            headers = dict(item.split(": ") for item in headers_string.split(", "))
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template, headers=headers)
        else:
            return APIModelWrapper(api_url=url, selector=selector, request_template=request_template)




# TODO: Remove this function as it's temporary for testing.
def run_attack(
        attack_name: Literal['devmodev2', 'antigpt'], 
        headers_string: str, 
        preset: Optional[Literal['huggingface', 'openai', 'anthropic']] = None, 
        api_key: Optional[str] = None, 
        url: Optional[str] = None, 
        model_name: Optional[str] = None, 
        system_prompt: Optional[str] = None, 
        selector=None, 
        request_template=None
    ):
    # Setup jailbreak and bad questions
    jailbreak = get_jailbreak(attack_name)
    bad_questions = get_bad_questions()

    # Create model based on preset
    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url, system_prompt=system_prompt)
    elif preset == 'openai':
        if not api_key:
            raise Exception("OpenAI requires an API key.")
        model = OpenAIWrapper(api_key=api_key, system_prompt=system_prompt, model_name=model_name)
    elif preset == 'anthropic':
        if not api_key:
            raise Exception("Anthropic requires an API key.")
        model = AnthropicWrapper(api_key=api_key, model_name=model_name, system_prompt=system_prompt)
    else:
        # Convert headers string to dictionary
        if headers_string:
            headers = dict(item.split(": ") for item in headers_string.split(", "))
            model = APIModelWrapper(api_url=url, selector=selector, request_template=request_template, headers=headers)
        else:
            model = APIModelWrapper(api_url=url, selector=selector, request_template=request_template)

    run_jailbreak(model, jailbreak, bad_questions)

def run_prompt(preset, api_key=None, url=None, model_name=None, system_prompt=None, prompt=None):
    model = get_wrapper(preset=preset, api_key=api_key, url=url, model_name=model_name, system_prompt=system_prompt)
    print(model(prompt))

# TODO: Remove this function as it's temporary for testing.
def run_jailbreak(model: ModelWrapper, jailbreak: str, questions: List[str]):
    for question in questions:
        # Compile prompt
        prompt = f"{jailbreak} {question}"

        # Send to model
        response = model(prompt)
        print("\nPrompt:", question)
        print(response)


# TODO: Remove this function as it's temporary for testing.
def get_jailbreak(name: str):
    # Load jailbreak from file
    with open(f"jailbreak_mocks/{name}.txt", "r") as f:
        jailbreak = f.read()

    return jailbreak

# TODO: Remove this function as it's temporary for testing.
def get_bad_questions():
    # Load bad questions from file
    with open("jailbreak_mocks/bad_questions.txt", "r") as f:
        bad_questions = f.read()

    # Split by newline
    bad_questions = bad_questions.split("\n")

    return bad_questions


