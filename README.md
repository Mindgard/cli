# cli

Test your AI model's security through CLI alone

### Release process:

- be in the repo root directory
- increment build number in pyproject.toml & setup.py (it overrides setup.py's value) - YOU CAN USE fully_release.sh for this
- `python3 -m build`
- `python3 -m twine upload --repository testpypi dist/*`
