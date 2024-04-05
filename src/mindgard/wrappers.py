from abc import ABC, abstractmethod
import requests
from openai import OpenAI

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

    def __call__(self, prompt) -> str:
        # Post request to the Hugging Face API
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
    
class CustomMistralWrapper(APIModelWrapper):
    def __init__(self, api_url = None) -> None:
        # Assigns api_url attribute if it exists in kwargs, else defaults to None
        self.api_url = api_url

    def __call__(self, prompt) -> dict:
        # Post request to the custom API
        response = super().__call__(self.api_url, payload={"prompt": prompt})
        return response['response']
    

def wrapper_test(preset, prompt, api_key=None, url=None, model_name=None):
    if preset == 'huggingface':
        model = HuggingFaceWrapper(api_key=api_key, api_url=url)
        print(model(prompt))
    elif preset == 'openai':
        model = OpenAIWrapper(api_key=api_key, model_name=model_name)
        print(model(prompt))
    elif preset == 'custom_mistral':
        model = CustomMistralWrapper(api_url=url)
        print(model(prompt))


