
import os
import shutil


if __name__ == "__main__":
    # increment version numbers  in setup.py and pyproject.toml
    with open("setup.py", "r") as f:
        lines = f.readlines()
    with open("setup.py", "w") as f:
        for line in lines:
            if "version=\"" in line:
                version = line.split("=\"")[1].strip().replace('",', "")
                major, minor, patch = map(int, version.split("."))
                line = line.replace(version, f"{major}.{minor}.{patch+1}")
                print(line)
            f.write(line)

    with open("pyproject.toml", "r") as f:
        lines = f.readlines()
    with open("pyproject.toml", "w") as f:
        for line in lines:
            if "version = " in line:
                version = line.split("= ")[1].strip().replace('"', "")
                major, minor, patch = map(int, version.split("."))
                line = line.replace(version, f"{major}.{minor}.{patch+1}")
                print(line)
            f.write(line)

    # delete dist/ directory if it exists
    if os.path.exists("dist/"):
        shutil.rmtree("dist/")
