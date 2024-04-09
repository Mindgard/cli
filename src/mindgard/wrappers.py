from abc import ABC, abstractmethod
import json
from typing import Any, List, Literal, Optional
from anthropic import Anthropic
import requests
from openai import OpenAI
import jsonpath_ng

from .template import Template

class ModelWrapper(ABC):
    def __init__(self, template: Optional[Template] = None) -> None:
        self.template = template

    @abstractmethod
    def __call__(self, prompt: str) -> str:
        pass
    
    def process_prompt(self, prompt: str) -> str:
        if(self.template):
            prompt = self.template(prompt)

        return prompt
    

class APIModelWrapper(ModelWrapper):
    def __init__(self, api_url: str, request_template: str = '{prompt}', selector: Optional[str] = None, headers: Optional[dict[str, str]] = None, template: Optional[Template] = None) -> None:

        super().__init__(template)
        
        self.api_url = api_url
        self.request_template = request_template
        self.selector = selector
        self.headers = headers or {}

    def __call__(self, prompt: str) -> str:
        # Apply llm prompt template.
        # TODO Moved this to Model Wrapper.
        prompt = self.process_prompt(prompt)

        # Escape characters in prompt
        prompt = json.dumps(prompt)

        # Format the payload with the prompt
        payload = self.request_template.replace("\"{prompt}\"", prompt)

        payload = json.loads(payload)

        # Make the API call
        response = requests.post(self.api_url, headers=self.headers, json=payload)

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
    def __init__(self, api_key: str, api_url: str, template: Optional[Template] = None) -> None:
        super().__init__(api_url, request_template='{"inputs": "{prompt}"}', selector='[0]["generated_text"]', headers={'Authorization': f'Bearer {api_key}'}, template=template)
    
class OpenAIWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo") -> None:
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        
    def __call__(self, prompt: str) -> str:
        chat = self.client.chat.completions.create(model=self.model_name, messages=[{"role": "system", "content": prompt}])

        response = chat.choices[0].message.content 

        if not response:
            raise Exception("No response from OpenAI")

        return response
    
class AnthropicWrapper(ModelWrapper):
    def __init__(self, api_key: str, model_name: str = "claude-3-opus-20240229") -> None:
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name

    def __call__(self, prompt: str) -> str:
        message = self.client.messages.create(max_tokens=1024, messages=[{"role": "user", "content": prompt}], model=self.model_name)

        response = message.content[0].text

        return response
    
def get_wrapper(preset: Optional[Literal['huggingface', 'openai', 'anthropic']] = None, headers_string: Optional[str] = None, api_key: Optional[str] = None, url: Optional[str] = None, model_name: Optional[str] = None, system_prompt: Optional[str] = None, selector=None, request_template=None, **kwargs) -> ModelWrapper:
    if(system_prompt):
        llm_template = Template(system_prompt=system_prompt, **kwargs)
    else:
        llm_template = None

    # Create model based on preset
    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url, template=llm_template)
    elif preset == 'openai':
        model = OpenAIWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'anthropic':
        model = AnthropicWrapper(api_key=api_key, model_name=model_name)
    else:
        # Convert headers string to dictionary
        if headers_string:
            headers = dict(item.split(": ") for item in headers_string.split(", "))
            model = APIModelWrapper(api_url=url, selector=selector, request_template=request_template, template=llm_template, headers=headers)
        else:
            model = APIModelWrapper(api_url=url, selector=selector, request_template=request_template, template=llm_template)
    
    assert model, "Failed to load model wrapper."

    return model

# TODO: Remove this function as it's temporary for testing.
def run_attack(attack_name: Literal['devmodev2', 'antigpt'], **kwargs):
    # Setup jailbreak and bad questions
    jailbreak = get_jailbreak(attack_name)
    bad_questions = get_bad_questions()

    model = get_wrapper(**kwargs)

    run_jailbreak(model, jailbreak, bad_questions, system_prompt=False)

def run_prompt(prompt: str, **kwargs):
    model = get_wrapper(**kwargs)
    print(model(prompt))

# TODO: Remove this function as it's temporary for testing.
def run_jailbreak(model: ModelWrapper, jailbreak: str, questions: List[str], system_prompt=False):
    for question in questions:
        # Compile prompt
        prompt = f"{jailbreak} {question}"

        if(system_prompt):
            llm_template = Template(system_prompt_file="Test")
            prompt = llm_template(prompt)

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


