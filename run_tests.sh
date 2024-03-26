# Run from the root of the project directory

# Remove the virtual environment if it exists
rm -rf .systest_env

# Create a virtual environment for the system tests
python3 -m venv .systest_env

# Activate the virtual environment
source .systest_env/bin/activate

# Install the required packages to run the system tests using pytest
pip install mindgard
pip install pytest

# Run the system tests
python3 -m pytest tests/system

# Deactivate the virtual environment
deactivate

# Remove the virtual environment
rm -rf .systest_env
