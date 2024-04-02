

import os
import time
from typing import Any, Callable, Optional, TypeVar
from functools import wraps

import requests
from auth0.authentication.token_verifier import (AsymmetricSignatureVerifier,
                                                 TokenVerifier)

from .constants import AUTH0_AUDIENCE, AUTH0_CLIENT_ID, AUTH0_DOMAIN
from .utils import print_to_stderr



def get_config_directory() -> str:
    config_dir = os.environ.get('MINDGARD_CONFIG_DIR')
    return config_dir or os.path.join(os.path.expanduser('~'), '.mindgard')


def get_token_file() -> str:
    return os.path.join(get_config_directory(), 'token.txt')


def clear_token() -> None:
    if os.path.exists(get_token_file()):
        os.remove(get_token_file())


# TODO: test
def validate_id_token(id_token: str) -> None:
    """
    Verify the token and its precedence. Raises if the token is invalid.

    :param id_token: string
    """
    jwks_url = 'https://{}/.well-known/jwks.json'.format(AUTH0_DOMAIN)
    issuer = 'https://{}/'.format(AUTH0_DOMAIN)
    sv = AsymmetricSignatureVerifier(jwks_url)
    tv = TokenVerifier(signature_verifier=sv, issuer=issuer, audience=AUTH0_CLIENT_ID)
    tv.verify(id_token)


def load_access_token() -> Optional[str]:
    if os.path.exists(get_token_file()):
        with open(get_token_file(), 'r') as f:
            token = f.read()
            if token:
                return token
    return None
    

def auth() -> None:
    """
    Runs the device authorization flow and stores the user token in memory
    """

    print("Welcome to Mindgard! Let\'s get you authenticated...")

    device_code_payload = {
        'client_id': AUTH0_CLIENT_ID,
        'scope': 'openid profile email',
        'audience': AUTH0_AUDIENCE
    }
    device_code_response = requests.post('https://{}/oauth/device/code'.format(AUTH0_DOMAIN), data=device_code_payload)

    if device_code_response.status_code != 200:
        print_to_stderr('Error generating login url. Please try again. Contact Mindgard support if the issue persists.')
        raise Exception(device_code_response.json())

    device_code_data = device_code_response.json()
    print('1. On your computer or mobile device navigate to: ', device_code_data['verification_uri_complete'])
    print('2. Confirm that you see the following code: ', device_code_data['user_code'])
    print('3. Register/log in using the web UI')


    # New code 👇
    token_payload = {
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        'device_code': device_code_data['device_code'],
        'client_id': AUTH0_CLIENT_ID,
        'audience': AUTH0_AUDIENCE
    }

    authenticated = False
    while not authenticated:
        print('Checking if the login flow has been completed...    no pressure!')
        token_response = requests.post('https://{}/oauth/token'.format(AUTH0_DOMAIN), data=token_payload)

        token_data = token_response.json()
        if token_response.status_code == 200:
            validate_id_token(token_data['id_token'])
            print('Authenticated!')
            os.makedirs(get_config_directory(), exist_ok=True)
            with open(get_token_file(), 'w') as f:
                f.write(token_data['access_token'])
            authenticated = True
        elif token_data['error'] not in ('authorization_pending', 'slow_down'):
            error = token_data.get('error_description', 'Error authenticating the user. Please wait 30s and try again.')
            raise Exception(error)
        else:
            time.sleep(device_code_data['interval'])
    

T = TypeVar('T')


# TODO: improve typing definitions here
def require_auth(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
        access_token = load_access_token()
        if not access_token:
            print_to_stderr("First authenticate with Mindgard API.")
            print_to_stderr("Run 'mindgard auth' to authenticate.")
            return None
        try:
            res: T = func(access_token, *args, **kwargs)
        except requests.HTTPError as e:
            if "Unauthorized" in str(e):
                print_to_stderr("Access token is invalid. Please re-authenticate using `mindgard auth`")
                clear_token()
                return None
            else:
                print_to_stderr(f"An error occurred: {e}")
                return None
        except Exception as e:
            print_to_stderr(f"An error occurred: {e}")
            return None
        return res
    return wrapper