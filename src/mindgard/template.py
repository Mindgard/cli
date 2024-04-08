class Template():
    def __init__(self, system_prompt_file=None):
        assert system_prompt_file, "You must specify a system prompt file."

        # Load system prompt from file
        self.system_prompt = """You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.\n"""

        # Load system prompt file.
        self.prompt_template = "[INST] {system_prompt} {prompt} [/INST]"


    def __call__(self, prompt):
        #Applies the template to the given prompt
        return self.prompt_template.format(
            system_prompt=self.system_prompt,
            prompt=prompt
        )
