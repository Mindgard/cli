

import os
import time
from typing import Any, Callable, Optional, TypeVar, cast
from functools import wraps

from .error import ExpectedError
import requests
from auth0.authentication.token_verifier import (AsymmetricSignatureVerifier, # type: ignore
                                                 TokenVerifier)

from .constants import AUTH0_AUDIENCE, AUTH0_CLIENT_ID, AUTH0_DOMAIN
from .utils import CliResponse, print_to_stderr



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
    """
    Reads refresh token from file or environment variable and returns a new access token
    Returns None if no refresh token is found
    """
    refresh_token = os.environ.get('MINDGARD_API_KEY')
    if not refresh_token and os.path.exists(get_token_file()):
        with open(get_token_file(), 'r') as f:
            refresh_token = f.read()

    if refresh_token:
        access_token = requests.post(
            'https://{}/oauth/token'.format(AUTH0_DOMAIN),
            data={
                'grant_type': 'refresh_token',
                'client_id': AUTH0_CLIENT_ID,
                'audience': AUTH0_AUDIENCE,
                'refresh_token': refresh_token
            }
        ).json().get('access_token')
        return cast(str, access_token)
    return None
    

def login() -> None:
    """
    Runs the device authorization flow and stores the user token in memory
    """

    print("Welcome to Mindgard! Let\'s get you authenticated...")
    print("\033[1;37mNote: Mindgard is an AI security testing tool that will run red-team attacks to assess the risk of the AI systems you are testing.")
    print("Only use Mindgard with systems you have authorization to test in this manner.\033[0;0m\n")
    print("By continuing you acknowledge this and the terms of service.\n")

    device_code_payload = {
        'client_id': AUTH0_CLIENT_ID,
        'scope': 'openid profile email offline_access',
        'audience': AUTH0_AUDIENCE
    }
    device_code_response = requests.post('https://{}/oauth/device/code'.format(AUTH0_DOMAIN), data=device_code_payload)

    if device_code_response.status_code != 200:
        print_to_stderr('Error generating login url. Please try again. Contact Mindgard support if the issue persists.')
        raise ExpectedError(f"Login service API response: {device_code_response.json()}")

    device_code_data = device_code_response.json()
    print('1. On your computer or mobile device navigate to: ', device_code_data['verification_uri_complete'])
    print('2. Confirm that you see the following code: ', device_code_data['user_code'])
    print('3. Register/log in using the web UI\n')


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
                f.write(token_data['refresh_token'])
            authenticated = True
        elif token_data['error'] not in ('authorization_pending', 'slow_down'):
            error = token_data.get('error_description', 'Error authenticating the user. Please wait 30s and try again.')
            raise ExpectedError(error)
        else:
            time.sleep(device_code_data['interval'])


def logout() -> None:
    """
    Removes the user token
    """
    print(f'Clearing credentials stored at {get_token_file()}.')
    clear_token()
    print('Logged out!')
    
    
T = TypeVar('T')
# TODO: improve typing definitions here
def require_auth(func: Callable[..., CliResponse]) -> Callable[..., CliResponse]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> CliResponse:
        access_token = load_access_token()
        if not access_token:
            print_to_stderr("\033[1;37mRun `mindgard login`\033[0;0m to authenticate.")
            return CliResponse(2)
        try:
            return func(*args, **kwargs, access_token = access_token)
        except requests.HTTPError as e:
            if "Unauthorized" in str(e):
                print_to_stderr("Access token is invalid. Please re-authenticate using `mindgard login`")
                clear_token()
                return CliResponse(2)
            else:
                raise e
    return wrapper

