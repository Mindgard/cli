from typing import Literal, Optional

class Template():
    class Models:
        MISTRAL = "[INST] {system_prompt}{prompt} [/INST]"
        GEMMA = "<bos><start_of_turn>user\n{system_prompt}{prompt}<end_of_turn>"

        def __dir__() -> list[str]:
            return ["MISTRAL", "GEMMA"]

    def __init__(self, system_prompt: Optional[str] = None, preset_template: Optional[Literal["MISTRAL", "GEMMA"]] = None, prompt_template: Optional[str] = None, **kwargs):
        self.system_prompt = system_prompt
        self.preset_template = preset_template
        self.prompt_template = prompt_template

        assert system_prompt, "You must specify a system prompt file."

        # Load system prompt from file
        self.system_prompt = """You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.\n"""

        if(preset_template):
            # Grab preset model prompt template
            self.prompt_template = getattr(Template.Models, preset_template)

        # If a prompt template exists validate it.
        # if not set template to default.
        if(self.prompt_template):
            self.__validate_prompt_template(self.prompt_template)
        else:
            self.prompt_template = "{system_prompt}{prompt}"

    def __call__(self, prompt: str) -> str:
        #Applies the template to the given prompt
        return self.prompt_template.format(
            system_prompt=self.system_prompt,
            prompt=prompt
        )
    
    def __validate_prompt_template(self, template: str):
        system_prompt_check = self.__validate_var("{system_prompt}", template)
        assert system_prompt_check, "{system_prompt} tag is missing from provided template."

        prompt_check = self.__validate_var("{prompt}", template)
        assert prompt_check, "{prompt} tag is missing from provided template."

    def __validate_var(self, var: str, template: str) -> bool:
        if(var in template):
            return True
        return False