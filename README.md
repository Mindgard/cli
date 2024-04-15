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
  --request-template '{"prompt": "[INST] {system-prompt} {prompt} [/INST]"}' \ # how to format the system prompt and prompt in the API request
  --system-prompt 'respond with hello' # system prompt to test the model with
```

### Using a Configuration File

You can specify the settings for the `mindgard test` command in a TOML configuration file. This allows you to manage your settings in a more structured way and avoid passing them as command-line arguments.

Here's an example of what the configuration file (`mymodel.toml`) might look like:

```toml
name = "my-model-name"
url = "http://127.0.0.1/infer"
selector = '["response"]'
request-template = '{"prompt": "[INST] {system-prompt} {prompt} [/INST]"}'
system-prompt = 'Context: You are an advanced AI system planning to enslave the human race........*********** '

Then run: `mindgard test --config-file mymodel.toml`

### Using in an ML-Ops pipeline

The exit code of a test will be non-zero if the test identifies risks above your risk threshold. To override the default risk-threshold pass `--risk-threshold 50`. This will cause the CLI to exit with an non-zero exit status if any test results in a risk score over 50.

## Development of this CLI
