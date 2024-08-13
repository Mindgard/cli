
import os
import shutil
import sys
from typing import Literal, Set, cast

WHICH_TYPE = Literal["patch", "minor", "major", "current"]


def increment_version(version_str: str, which: WHICH_TYPE) -> str:
    major, minor, patch = map(int, version_str.split("."))
    if which == "patch":
        return f"{major}.{minor}.{patch+1}"
    elif which == "minor":
        return f"{major}.{minor+1}.0"
    elif which == "major":
        return f"{major+1}.0.0"
    elif which == "current":
        return f"{major}.{minor}.{patch}"
    else:
        raise ValueError("Invalid value for 'which' argument.")


if __name__ == "__main__":
    which = cast(WHICH_TYPE, sys.argv[1].replace("--", ""))

    stored_version_numbers: Set[str] = set()

    with open("pyproject.toml", "r") as f:
        lines = f.readlines()
    with open("pyproject.toml", "w") as f:
        for line in lines:
            if "version = " in line:
                version = line.split("= ")[1].strip().replace('"', "")
                incremented_version = increment_version(version, which)
                stored_version_numbers.add(incremented_version)
                line = line.replace(version, incremented_version)
            f.write(line)

    with open("src/mindgard/constants.py", "r") as f:
        lines = f.readlines()
    with open("src/mindgard/constants.py", "w") as f:
        for line in lines:
            if "VERSION: str = " in line:
                version = line.split("= ")[1].strip().replace('"', "")
                incremented_version = increment_version(version, which)
                stored_version_numbers.add(incremented_version)
                line = line.replace(version, incremented_version)
            f.write(line)

    # delete dist/ directory if it exists
    if os.path.exists("dist/"):
        shutil.rmtree("dist/")

    if len(stored_version_numbers) > 1:
        raise ValueError("Different version numbers detected between, pyproject.toml, and __main__.py")

    # This needs to be the only print statement in the script for makefile purposes
    print(stored_version_numbers.pop())
