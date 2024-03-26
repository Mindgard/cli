

import argparse
import os
from typing import Callable
import requests

from .auth import auth, clear_token, load_access_token


access_token: str = ""


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
    res = requests.get("https://api.sandbox.mindgard.ai/api/v1/attacks/categories", headers={"Authorization": f"Bearer {access_token}"})
    return res


def main():
    global access_token
    access_token = load_access_token()

    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('list', help='List the possible attack categories', )
    subparsers.add_parser('auth', help='Authenticate with Mindgard API')
    args = parser.parse_args()

    if args.command == 'auth':
        auth()
    elif args.command == 'list':
        list()
    else:
        print('Hey give us a command. Use list or auth.')


if __name__ == '__main__':
    main()