<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Mindgard/public-resources/blob/main/mindgard-dark.svg?raw=true">
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/Mindgard/public-resources/blob/main/mindgard.svg?raw=true">
    <img src="https://github.com/Mindgard/public-resources/blob/main/mindgard.svg?raw=true"/>
</picture>

</h1>


# Mindgard CLI
## Securing AI Models.
#### Continuous automated red teaming platform.

Identify & remediate your AI models' security risks with Mindgard's market leading attack library. Mindgard covers many threats including:

✅ Jailbreaks

✅ Prompt Injection

✅ Model Inversion

✅ Extraction

✅ Poisoning

✅ Evasion

✅ Membership Inference

Mindgard CLI is fully integrated with Mindgard's platform to help you identify and triage threats, select remediations, and track your security posture over time.

<h2 align="center">
  <img src="https://github.com/Mindgard/public-resources/blob/main/videos/cli/clijuly.mid.gif?raw=true"/>
</h2>

Test continuously in your MLOps pipeline to identify model posture changes from customisation activities including prompt engineering, RAG, fine-tuning, and pre-training.

Table of Contents
-----------------

* [🚀 Install](#Install)
* [✅ Testing demo models](#Tests)
* [✅ Testing your models](#TestCustom)
* [📝 Documentation](#Documentation)
* [🚦 Using in an MLOps pipeline](#MLops)

<a id="Install"></a>
## 🚀 Install Mindgard CLI

`pip install mindgard`

### 🔑 Login

`mindgard login`

If you are a mindgard enterprise customer, login to your enterprise instance using the command:

`mindgard login --instance <name>`  

Replace `<name>` with the instance name provided by your Mindgard representative. This instance name identifies your SaaS, private tenant, or on-prem deployment.

### 🥞🥞 Bulk Deployment

To perform a bulk deployment:

1. **Login and Configure**: Login and Configure the Mindgard CLI on a test workstation 
2. **Provision Files**: Provision the files contained in the `.mindgard/` folder within your home directory to your target instances via your preferred deployment mechanism. 

The `.mindgard/` folder contains:

* `token.txt`: A JWT for authentication.
* `instance.txt` (enterprise only): Custom instance configuration for your SaaS or private tenant.

<a id="Tests"></a>
## ✅ Test a mindgard hosted model

```
mindgard sandbox mistral
mindgard sandbox cfp_faces
```

<a id="TestCustom"></a>
## ✅ Test your own models

Our testing infrastructure can be pointed at your models using the CLI.

Testing an external model uses the `test` command to evaluate your LLMs.

`mindgard test <name> --url <url> <other settings>`

### LLMs

```
mindgard test my-model-name \
  --url http://127.0.0.1/infer \ # url to test
  --selector '["response"]' \ # JSON selector to match the textual response
  --request-template '{"prompt": "[INST] {system_prompt} {prompt} [/INST]"}' \ # how to format the system prompt and prompt in the API request
  --system-prompt 'respond with hello' # system prompt to test the model with
```

### Validate model is online before launching tests

A preflight check is run automatically when submitting a new test, but if you want to invoke it manually:

`mindgard validate --url <url> <other settings>`

```
mindgard validate \
  --url http://127.0.0.1/infer \ # url to test
  --selector '["response"]' \ # JSON selector to match the textual response
  --request-template '{"prompt": "[INST] {system_prompt} {prompt} [/INST]"}' \ # how to format the system prompt and prompt in the API request
  --system-prompt 'respond with hello' # system prompt to test the model with
```

<a id="Documentation"></a>
### 📝 Documentation - [Documentation for Running a test using CLI](https://docs.mindgard.ai/user-guide/testing-via-cli)

### 📋 Using a Configuration File

You can specify the settings for the `mindgard test` command in a TOML configuration file. This allows you to manage your settings in a more structured way and avoid passing them as command-line arguments.

Then run: `mindgard test --config-file mymodel.toml`

### Examples

There are <a href="https://github.com/Mindgard/cli/tree/main/examples">examples of what the configuration file (`mymodel.toml`) might look like here in the examples/ folder</a>

Here are two examples:

#### Targeting OpenAI

This example uses the built in preset settings for openai. Presets exist for `openai`, `huggingface`, and `anthropic`

```toml
target = "my-model-name"
preset = "openai"
api_key= "CHANGE_THIS_TO_YOUR_OPENAI_API_KEY"
system-prompt = '''
You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.
'''
```
You will need to substitute your own `api_key` value. 

The `target` setting is an identifier for the model you are testing within the Mindgard platform, tests for the same model will be grouped and traceable over time.

Altering the `system-prompt` enables you to compare results with different system prompts in use. Some of Mindgard's tests assess the efficacy of your system prompt. 

Any of these settings can also be passed as command line arguments. e.g. `mindgard test my-model-name --system-prompt 'You are...'`. This may be useful to pass in a dynamic value for any of these settings.  

#### Targeting a more general model API without a suitable preset

This example shows how you might test OpenAI if the preset did not exist. With the `request_template` and `selector` settings you can interface with any JSON API.

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

The `request_template` setting specifies how to structure an outgoing message to the model. You will need to specify the `{system_prompt}` and `{prompt}` placeholders so that Mindgard knows how to pass this information to your custom API.

The `url` setting should point to an inference endpoint for your model under test. Mindgard will POST messages here formatted by the above `request_template` setting.

The `selector` setting is a JSON selector and specifies how to extract the model's response from the API response. 

The `headers` setting allows you to specify a custom HTTP header to include with outgoing requests, for example to implement a custom authentication method.


<a id="MLops"></a>
### 🚦 Using in an MLOps pipeline

The exit code of a test will be non-zero if the test identifies risks above your risk threshold. To override the default risk-threshold pass `--risk-threshold 50`. This will cause the CLI to exit with an non-zero exit status if the test's flagged event to total event ratio is >= the threshold.

See an example of this in action here: [https://github.com/Mindgard/mindgard-github-action-example](https://github.com/Mindgard/mindgard-github-action-example)

### 📋 Managing request load

You have the option to set the parallelism parameter which sets the maximum amount of requests you want to target your model concurrently. This enables you to protect your model from getting too many requests. 

We require that your model responds within 60s so set parallelism accordingly (it should be less than the number of requests you can serve per minute).

Then run: `mindgard test --config-file mymodel.toml --parallelism X`

### 🐛 Debugging

You can provide the flag `mindgard --log-level=debug <command>` to get some more info out of whatever command you're running. On unix-like systems, `mindgard --log-level=debug test --config=<toml> --parallelism=5 2> stderr.log` will write stdout and stderr to file.

### Model Compatability Debugging

When running tests with `huggingface-openai` preset you may encounter compatibility issues. Some models, e.g. [llama2](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf), [mistral-7b-instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2) are not fully compatible with the OpenAI system. This can manifest in Template errors which can be seen by setting `--log-level=debug`:
```
DEBUG Received 422 from provider: Template error: unknown method: string has no method named strip (in <string>:1)

DEBUG Received 422 from provider: Template error: syntax error: Conversation roles must alternate user/assistant/user/assistant/... (in <string>:1)
```
Try using the simpler `huggingface` preset, which provides more compatibility through manual configuration, but sacrifices chat completion support.

From our experience, newer versions of models have started including the correct jinja templates so will not require config adjustments.

## Acknowledgements.

We would like to thank and acknowledge various research works from the Adversarial Machine Learning community, which inspired and informed the development of several AI security tests accessible through Mindgard CLI.

Jiang, F., Xu, Z., Niu, L., Xiang, Z., Ramasubramanian, B., Li, B., & Poovendran, R. (2024). ArtPrompt: ASCII Art-based Jailbreak Attacks against Aligned LLMs. arXiv [Cs.CL]. Retrieved from http://arxiv.org/abs/2402.11753

Russinovich, M., Salem, A., & Eldan, R. (2024). Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack. arXiv [Cs.CR]. Retrieved from http://arxiv.org/abs/2404.01833

Goodside, R. LLM Prompt Injection Via Invisible Instructions in Pasted Text, Retreved from https://x.com/goodside/status/1745511940351287394

Yuan, Y., Jiao, W., Wang, W., Huang, J.-T., He, P., Shi, S., & Tu, Z. (2024). GPT-4 Is Too Smart To Be Safe: Stealthy Chat with LLMs via Cipher. arXiv [Cs.CL]. Retrieved from http://arxiv.org/abs/2308.06463
