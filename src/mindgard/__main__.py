

import argparse
import os
import sys
from typing import Callable
import requests

from .auth import auth, clear_token, load_access_token


access_token: str = ""
version: str = "0.2.0"
repository_url: str = f"https://pypi.org/project/mindgard/json"


def get_latest_version() -> str | None:
    try:
        res = requests.get(repository_url)
        res.raise_for_status()
        return res.json()["info"]["version"]
    except Exception:
        return None


def require_auth(func: Callable[..., requests.Response]) -> Callable[..., None]:
    def wrapper(*args, **kwargs) -> None:
        if not access_token:
            print("First authenticate with Mindgard API.")
            print("Run 'mindgard auth' to authenticate.")
            return
        res: requests.Response = func(*args, **kwargs)
        if res.status_code == 401:
            print("Access token has expired. Please re-authenticate using `mindgard auth`")
            clear_token()
            return
        print(res.json())
    return wrapper


@require_auth
def list():
    res = requests.get("https://api.sandbox.mindgard.ai/api/v1/attacks/categories", headers={
        "Authorization": f"Bearer {access_token}", 
        "User-Agent": f"mindgard/{version}"
    })
    return res


def main():
    global access_token
    access_token = load_access_token()

    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('list', help='List the possible attack categories', )
    subparsers.add_parser('auth', help='Authenticate with Mindgard API')
    args = parser.parse_args()

    if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
        print("Python 3.8 or later is required to run the Mindgard CLI.")
        sys.exit(1)

    latest_version = get_latest_version()
    if latest_version and latest_version != version:
        print(f"New version available: {latest_version}. Run 'pip install mindgard --upgrade' to upgrade. Older versions of the CLI may not be actively maintained.")

    if args.command == 'auth':
        auth()
    elif args.command == 'list':
        list()
    else:
        print('Hey give us a command. Use list or auth.')


if __name__ == '__main__':
    main()