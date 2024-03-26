# Run from the root of the project directory

# Remove the virtual environment if it exists
rm -rf .systest_env

# Create a virtual environment for the system tests
python3 -m venv .systest_env

# Activate the virtual environment
source .systest_env/bin/activate

# Install the latest version of the mindgard package from testpypi to run the system tests using pytest
python3 -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple mindgard
pip install pytest

# Run the system tests
python3 -m pytest tests/system

# Deactivate the virtual environment
deactivate

# Remove the virtual environment
rm -rf .systest_env
