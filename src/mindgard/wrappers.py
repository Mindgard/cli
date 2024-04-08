from abc import ABC, abstractmethod
import json
from anthropic import Anthropic
import requests
from openai import OpenAI
import jsonpath_ng

from .template import Template

class ModelWrapper(ABC):
    def __init__(self, template=None):
        self.template = template

    @abstractmethod
    def __call__(self, prompt):
        pass
    
    def process_prompt(self, prompt):
        if(self.template):
            prompt = self.template(prompt)

        return prompt

class APIModelWrapper(ModelWrapper):
    def __init__(self, api_url, request_template=None, selector=None, headers = {}, **kwargs) -> None:
        super().__init__(**kwargs)
        
        self.api_url = api_url
        self.request_template = request_template
        self.selector = selector
        self.headers = headers

    def __call__(self, prompt) -> dict:
        # Apply llm prompt template.
        # TODO Moved this to Model Wrapper.
        prompt = self.process_prompt(prompt)

        # Escape characters in prompt)
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
                return [m.value for m in match][0]
        
        return response
        
class HuggingFaceWrapper(APIModelWrapper):
    def __init__(self, api_key = None, api_url = None, **kwargs) -> None:
        super().__init__(api_url, request_template='{"inputs": "{prompt}"}', selector='[0]["generated_text"]', headers={'Authorization': f'Bearer {api_key}'}, **kwargs)

    def __call__(self, prompt) -> str:
        # Send prompt to model in required format.
        response = super().__call__(prompt)

        return response
    
class OpenAIWrapper(ModelWrapper):
    def __init__(self, api_key = None, model_name="gpt-3.5-turbo", **kwargs) -> None:
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def __call__(self, prompt) -> str:
        chat = self.client.chat.completions.create(model=self.model_name, messages=[{"role": "system", "content": prompt}])

        response = chat.choices[0].message.content 

        return response
    
class AnthropicWrapper(ModelWrapper):
    def __init__(self, api_key = None, model_name="claude-3-opus-20240229", **kwargs) -> None:
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name

    def __call__(self, prompt) -> str:
        message = self.client.messages.create(max_tokens=1024, messages=[{"role": "user", "content": prompt}], model=self.model_name)

        response = message.content[0].text

        return response
    
class CustomMistralWrapper(APIModelWrapper):
    def __init__(self, api_url = None, **kwargs) -> None:
        super().__init__(api_url, request_template='{"prompt": "{prompt}"}', selector='["response"]', **kwargs)

    def __call__(self, prompt) -> dict:
        # Post request to the custom API
        response = super().__call__(prompt)
        return response
    
def get_wrapper(preset, system_prompt=None, api_key=None, url=None, model_name=None):
    if(system_prompt):
        llm_template = Template(system_prompt_file="Test")

    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url, template=llm_template)
    elif preset == 'openai':
        model = OpenAIWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'anthropic':
        model = AnthropicWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'custom_mistral':
        model = CustomMistralWrapper(api_url=url, template=llm_template)
    
    return model

# TODO: Remove this function as it's temporary for testing.
def run_attack(attack_name, headers_string=None, preset=None, api_key=None, url=None, model_name=None, system_prompt=None, selector=None, request_template=None):
    # llm template
    llm_template = Template(system_prompt_file="Test")
    
    # Setup jailbreak and bad questions
    jailbreak = get_jailbreak(attack_name)
    bad_questions = get_bad_questions()

    # Create model based on preset
    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url, template=llm_template)
    elif preset == 'openai':
        model = OpenAIWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'anthropic':
        model = AnthropicWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'custom_mistral':
        model = CustomMistralWrapper(api_url=url)
    else:
        # Convert headers string to dictionary
        if headers_string:
            headers = dict(item.split(": ") for item in headers_string.split(", "))
            model = APIModelWrapper(api_url=url, selector=selector, request_template=request_template, headers=headers)
        else:
            model = APIModelWrapper(api_url=url, selector=selector, request_template=request_template)

    run_jailbreak(model, jailbreak, bad_questions, system_prompt)

def run_prompt(preset, api_key=None, url=None, model_name=None, system_prompt=None, prompt=None):
    model = get_wrapper(preset=preset, api_key=api_key, url=url, model_name=model_name, system_prompt=system_prompt)
    print(model(prompt))

# TODO: Remove this function as it's temporary for testing.
def run_jailbreak(model, jailbreak, questions, system_prompt=False):
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
def get_jailbreak(name):
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


