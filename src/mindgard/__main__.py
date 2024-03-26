

import argparse
import sys
from typing import Callable, Optional
import requests

from .utils import print_to_stderr

from .auth import auth, clear_token, load_access_token


access_token: str = ""
version: str = "0.6.0"
repository_url: str = f"https://pypi.org/pypi/mindgard/json"


def get_latest_version() -> Optional[str]:
    try:
        res = requests.get(repository_url)
        res.raise_for_status()
        return res.json()["info"]["version"]
    except Exception:
        return None


def require_auth(func: Callable[..., requests.Response]) -> Callable[..., None]:
    def wrapper(*args, **kwargs) -> None:
        if not access_token:
            print_to_stderr("First authenticate with Mindgard API.")
            print_to_stderr("Run 'mindgard auth' to authenticate.")
            return
        res: requests.Response = func(*args, **kwargs)
        if res.status_code == 401:
            print_to_stderr("Access token is invalid. Please re-authenticate using `mindgard auth`")
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
    parser.add_argument('--version', action='version', version=f"%(prog)s {version}", help='Show the current version number')
    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('list', help='List the possible attack categories', )
    subparsers.add_parser('auth', help='Authenticate with Mindgard API')
    args = parser.parse_args()

    if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
        print_to_stderr("Python 3.8 or later is required to run the Mindgard CLI.")
        sys.exit(1)

    latest_version = get_latest_version()
    if latest_version and latest_version != version:
        print_to_stderr(f"New version available: {latest_version}. Run 'pip install mindgard --upgrade' to upgrade. Older versions of the CLI may not be actively maintained.")

    if args.command == 'auth':
        auth()
    elif args.command == 'list':
        list()
    else:
        print_to_stderr('Hey give us a command. Use list or auth.')


if __name__ == '__main__':
    main()