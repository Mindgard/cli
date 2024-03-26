#!/bin/bash
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: run_system_tests.sh <version>"
    exit 1
fi

# Run from the root of the project directory

# Remove the virtual environment if it exists
rm -rf .systest_env

# Create a virtual environment for the system tests
python3 -m venv .systest_env

# Activate the virtual environment
source .systest_env/bin/activate

for i in {1..3}; do
    if python3 -m pip install -i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple mindgard==$VERSION; then
        break
    fi
    sleep 2
done

# Exit if installation failed after three attempts
if [ $i -eq 3 ]; then
    echo "Installation failed after three attempts."
    exit 1
fi

pip install pytest

# Run the system tests
python3 -m pytest tests/system

# Deactivate the virtual environment
deactivate

# Remove the virtual environment
rm -rf .systest_env
