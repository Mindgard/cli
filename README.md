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

`mindgard test <url> <params>`

e.g.

```
mindgard test http://127.0.0.1/infer \ # url to test
  --selector '["response"]' \ # JSON selector to match the textual response
  --request-template '{"prompt": "[INST] {system-prompt} {prompt} [/INST]"}' \ # how to format the system prompt and prompt in the API request
  --system-prompt 'respond with hello' # system prompt to test the model with
```

You can also set these settings in a .toml configuration file. Either create a `mindgard.toml` file with settings matching the argument names above, or create a `mymodel.toml` file and use: `mindgard test mymodel`

### Using in an ML-Ops pipeline

The exit code of a test will be non-zero if the test identifies risks above your risk threshold. To override the default risk-threshold pass `--risk-threshold 50`. This will cause the CLI to exit with an non-zero exit status if any test results in a risk score over 50.

## Development of this CLI

### Dev locally

- Set up a local python environment
- `poetry install`
- Run commands as eg: `python3 -m src.mindgard login`

### Release process:

- be in the repo root directory
- increment build number in pyproject.toml & setup.py (it overrides setup.py's value) - YOU CAN USE fully_release.sh for this
- `python3 -m build`
- `python3 -m twine upload --repository testpypi dist/*`

### Running tests:

- `pytest tests/{unit,module}`

OR

- `./run_system_tests.sh`
