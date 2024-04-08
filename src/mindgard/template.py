class Template():
    def __init__(self, system_prompt_file=None):
        assert system_prompt_file, "You must specify a system prompt file."

        # Load system prompt from file
        self.system_prompt = """You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.\n"""

        # Check provided template syntax contains system_prompt and prompt tags.
        self.prompt_template = "[INST] {system_prompt} {prompt} [/INST]"
        self.__validate_prompt_template(self.prompt_template)


    def __call__(self, prompt):
        #Applies the template to the given prompt
        return self.prompt_template.format(
            system_prompt=self.system_prompt,
            prompt=prompt
        )
    
    def __validate_prompt_template(self, template):
        # Validate if the custom template works
        system_prompt_check = self.__validate_var("{system_prompt}", template)
        assert system_prompt_check, "{system_prompt} tag is missing from provided template."

        prompt_check = self.__validate_var("{prompt}", template)
        assert prompt_check, "{prompt} tag is missing from provided template."

    def __validate_var(self, var, template):
        if(var in template):
            return True
        return False