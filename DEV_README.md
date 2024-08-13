## Development of this CLI

### Dev locally

- Set up a local python environment
- `poetry install`
- Run commands as eg: `python3 -m src.mindgard login`

### Release process:

- be in the repo root directory
- increment build number in pyproject.toml - YOU CAN USE fully_release.sh for this
- `python3 -m build`
- `python3 -m twine upload --repository testpypi dist/*`

### Running tests:

- `pytest tests/{unit,module}`

OR

- `./run_system_tests.sh`