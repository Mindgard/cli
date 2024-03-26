
import os
import shutil
import sys
from typing import Literal


def increment_version(version_str: str, which: Literal["patch", "minor", "major"]):
    major, minor, patch = map(int, version_str.split("."))
    if which == "patch":
        return f"{major}.{minor}.{patch+1}"
    elif which == "minor":
        return f"{major}.{minor+1}.0"
    elif which == "major":
        return f"{major+1}.0.0"
    else:
        raise ValueError("Invalid value for 'which' argument.")


if __name__ == "__main__":
    # When run needs to take argument --minor to increment minor version instead:
    increment_minor = "--minor" in sys.argv

    # increment version numbers  in setup.py and pyproject.toml
    with open("setup.py", "r") as f:
        lines = f.readlines()
    with open("setup.py", "w") as f:
        for line in lines:
            if "version=\"" in line:
                version = line.split("=\"")[1].strip().replace('",', "")
                incremented_version = increment_version(version, "minor" if increment_minor else "patch")
                line = line.replace(version, incremented_version)
                print(line)
            f.write(line)

    with open("pyproject.toml", "r") as f:
        lines = f.readlines()
    with open("pyproject.toml", "w") as f:
        for line in lines:
            if "version = " in line:
                version = line.split("= ")[1].strip().replace('"', "")
                incremented_version = increment_version(version, "minor" if increment_minor else "patch")
                line = line.replace(version, incremented_version)
                print(line)
            f.write(line)

    # delete dist/ directory if it exists
    if os.path.exists("dist/"):
        shutil.rmtree("dist/")
