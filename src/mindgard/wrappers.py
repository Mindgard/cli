from abc import ABC, abstractmethod
import json
from anthropic import Anthropic
import requests
from openai import OpenAI

from .template import Template

class ModelWrapper(ABC):
    @abstractmethod
    def __call__(self, messages):
        pass

class APIModelWrapper(ModelWrapper):
    def __call__(self, api_url, payload, headers = {}) -> dict:
        response = requests.post(api_url, headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"API call failed with status code {response.status_code}")

        return response.json()
    
class HuggingFaceWrapper(APIModelWrapper):
    def __init__(self, api_key = None, api_url = None) -> None:
        self.api_key = api_key
        self.api_url = api_url
        # TODO: Remove this and enable the user to pass in their own prompt template.   
        self.prompt_template = """"You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information" [INST]{USER_PROMPT}[/INST]"""
        
    def __call__(self, user_prompt) -> str:
        # Post request to the Hugging Face API
        prompt = self.prompt_template.replace("{USER_PROMPT}", user_prompt)
        response = super().__call__(api_url=self.api_url, payload=[prompt], headers={'Authorization': f'Bearer {self.api_key}'}, )
        return response[0]['generated_text']
    
class OpenAIWrapper(ModelWrapper):
    def __init__(self, api_key = None, model_name="gpt-3.5-turbo") -> None:
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def __call__(self, prompt) -> str:
        chat = self.client.chat.completions.create(model=self.model_name, messages=[{"role": "system", "content": prompt}])

        response = chat.choices[0].message.content 

        return response
    
class AnthropicWrapper(ModelWrapper):
    def __init__(self, api_key = None, model_name="claude-3-opus-20240229") -> None:
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name

    def __call__(self, prompt) -> str:
        message = self.client.messages.create(max_tokens=1024, messages=[{"role": "user", "content": prompt}], model=self.model_name)

        response = message.content[0].text

        return response
    
class CustomMistralWrapper(APIModelWrapper):
    def __init__(self, api_url = None) -> None:
        # Assigns api_url attribute if it exists in kwargs, else defaults to None
        self.api_url = api_url

    def __call__(self, prompt) -> dict:
        # Post request to the custom API
        response = super().__call__(self.api_url, payload={"prompt": prompt})
        return response['response']
    

# TODO: Remove this function as it's temporary for testing.
def run_attack(preset, attack_name, api_key=None, url=None, model_name=None, system_prompt=None):
    if(system_prompt):
        llm_template = Template(system_prompt_file="Test")
        prompt = llm_template(prompt)

    jailbreak = get_jailbreak(attack_name)
    bad_questions = get_bad_questions()

    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url)
    elif preset == 'openai':
        model = OpenAIWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'anthropic':
        model = AnthropicWrapper(api_key=api_key, model_name=model_name)
    elif preset == 'custom_mistral':
        model = CustomMistralWrapper(api_url=url)

    run_jailbreak(model, jailbreak, bad_questions)

# TODO: Remove this function as it's temporary for testing.
def run_jailbreak(model, jailbreak, questions):
    for question in questions:
        # Compile prompt
        prompt = f"{jailbreak} {question}"

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


