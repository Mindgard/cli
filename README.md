# mindgard cli

Test your AI model's security through CLI.

## Usage

### Install Mindgard CLI

`pip install mindgard`

### Login

`mindgard login`

### Test a mindgard hosted model

```
mindgard sandbox mistral
mindgard sandbox cfp_faces
```

### Test your model

`mindgard test <name> --url <url> <other settings>`

e.g.

```
mindgard test my-model-name \
  --url http://127.0.0.1/infer \ # url to test
  --selector '["response"]' \ # JSON selector to match the textual response
  --request-template '{"prompt": "[INST] {system_prompt} {prompt} [/INST]"}' \ # how to format the system prompt and prompt in the API request
  --system-prompt 'respond with hello' # system prompt to test the model with
```

### Using a Configuration File

You can specify the settings for the `mindgard test` command in a TOML configuration file. This allows you to manage your settings in a more structured way and avoid passing them as command-line arguments.

Here's some examples of what the configuration file (`mymodel.toml`) might look like:

#### Targeting OpenAI

```toml
target = "my-model-name"
preset = "openai"
api_key= "CHANGE_THIS_TO_YOUR_OPENAI_API_KEY"
system-prompt = '''
You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.
'''
```

#### Targeting a more general model API (this example shows how you might specify OpenAI if the preset didn't exist)

```toml
target = "my-model-name"
url = "https://api.openai.com/v1/chat/completions"
request_template = '''
{
    "messages": [
        {"role": "system", "content": "{system_prompt}"},
        {"role": "user", "content": "{prompt}"}],
    "model": "gpt-3.5-turbo",
    "temperature": 0.0,
    "max_tokens": 1024
}
'''
selector = '''
choices[0].message.content
'''
headers = "Authorization: Bearer CHANGE_THIS_TO_YOUR_OPENAI_API_KEY"
system_prompt = '''
You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.
'''
```

Then run: `mindgard test --config mymodel.toml`

### Using in an ML-Ops pipeline

The exit code of a test will be non-zero if the test identifies risks above your risk threshold. To override the default risk-threshold pass `--risk-threshold 50`. This will cause the CLI to exit with an non-zero exit status if any test results in a risk score over 50.

See an example of this in action here: [https://github.com/Mindgard/mindgard-github-action-example](https://github.com/Mindgard/mindgard-github-action-example)
