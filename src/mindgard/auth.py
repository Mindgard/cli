

import os
import time
from auth0.authentication.token_verifier import (
    AsymmetricSignatureVerifier,
    TokenVerifier,
)
import requests


AUTH0_DOMAIN="login.sandbox.mindgard.ai"
AUTH0_CLIENT_ID="U0OT7yZLJ4GEyabar11BENeQduu4MaNO"
AUTH0_AUDIENCE="https://marketplace-orchestrator.com"
ALGORITHMS = ['RS256']


def get_config_directory():
    config_dir = os.environ.get('MINDGARD_CONFIG_DIR')
    return config_dir or os.path.join(os.path.expanduser('~'), '.mindgard')


def get_token_file():
    return os.path.join(get_config_directory(), 'token.txt')


def clear_token():
    if os.path.exists(get_token_file()):
        os.remove(get_token_file())


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


def load_access_token():
    if os.path.exists(get_token_file()):
        with open(get_token_file(), 'r') as f:
            token = f.read()
            if token:
                return token
    

def auth():
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
        print('Error generating login url. Please try again. Contact Mindgard support if the issue persists.')
        raise Exception(device_code_response.json())

    print('Device code successful')
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
                global access_token
                access_token = token_data['access_token']
            authenticated = True
        elif token_data['error'] not in ('authorization_pending', 'slow_down'):
            error = token_data.get('error_description', 'Error authenticating the user. Please wait 30s and try again.')
            raise Exception(error)
        else:
            time.sleep(device_code_data['interval'])
    

