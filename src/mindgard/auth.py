import os
from typing import Any, Callable, Optional, TypeVar, cast
from functools import wraps

import requests
from auth0.authentication.token_verifier import (
    AsymmetricSignatureVerifier,  # type: ignore
    TokenVerifier,
)

from .utils import CliResponse, print_to_stderr
from .config import (
    get_token_file,
    get_instance_file,
    load_auth_config,
)
from .config import (
    is_instance_set,
    instance_auth_config,
    sandbox_auth_config,
    create_config_directory,
)
import requests
from .utils import print_to_stderr

from rich.console import Console

import json
import time


def clear_token() -> None:
    if os.path.exists(get_token_file()):
        os.remove(get_token_file())


def clear_instance() -> None:
    """
    Deletes the instance file
    """
    if os.path.exists(get_instance_file()):
        os.remove(get_instance_file())


def login(instance: str) -> None:
    """
    Runs the device authorization flow and stores the user token in memory.
    If instance is set by user, grab required instance variables from their deployment.

    :param instance: string
    """

    if not is_instance_set():
        print("Welcome to Mindgard! Let's get you authenticated...")
        print(
            "\033[1;37mNote: Mindgard is an AI security testing tool that will run red-team attacks to assess the risk of the AI systems you are testing."
        )
        print(
            "Only use Mindgard with systems you have authorization to test in this manner.\033[0;0m\n"
        )
        print("By continuing you acknowledge this and the terms of service.\n")

        if instance:
            customer_instance_response = requests.get(
                "https://api.{}.mindgard.ai/api/v1/cli/context".format(instance)
            )

            if customer_instance_response.status_code != 200:
                print_to_stderr(
                    "Error communicating with deployed instance. Please validate instance name and try again. Contact Mindgard support if the issue persists."
                )
                raise ValueError(
                    f"Error communicating with deployed instance: {customer_instance_response.json()}"
                )

            customer_instance_data = customer_instance_response.json()

            auth_configs = instance_auth_config(customer_instance_data)
        else:
            auth_configs = sandbox_auth_config()

        device_code_payload = {
            "client_id": auth_configs.AUTH0_CLIENT_ID,
            "scope": "openid profile email offline_access",
            "audience": auth_configs.AUTH0_AUDIENCE,
        }
        device_code_response = requests.post(
            "https://{}/oauth/device/code".format(auth_configs.AUTH0_DOMAIN),
            data=device_code_payload,
        )

        if device_code_response.status_code != 200:
            print_to_stderr(
                "Error generating login url. Please try again. Contact Mindgard support if the issue persists."
            )
            raise ValueError(
                f"Login service API response: {device_code_response.json()}"
            )

        device_code_data = device_code_response.json()
        print(
            "1. On your computer or mobile device navigate to: ",
            device_code_data["verification_uri_complete"],
        )
        print(
            "2. Confirm that you see the following code: ",
            device_code_data["user_code"],
        )
        print("3. Register/log in using the web UI\n")

        # New code 👇
        token_payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code_data["device_code"],
            "client_id": auth_configs.AUTH0_CLIENT_ID,
            "audience": auth_configs.AUTH0_AUDIENCE,
        }

        console = Console()
        with console.status("[bold green]Waiting for auth to complete...") as status:
            authenticated = False
            while not authenticated:
                token_response = requests.post(
                    "https://{}/oauth/token".format(auth_configs.AUTH0_DOMAIN),
                    data=token_payload,
                )

                token_data = token_response.json()
                if token_response.status_code == 200:
                    validate_id_token(
                        token_data["id_token"],
                        auth_configs.AUTH0_DOMAIN,
                        auth_configs.AUTH0_CLIENT_ID,
                    )
                    print("Authenticated!")
                    # Create config directory
                    create_config_directory()

                    with open(get_token_file(), "w") as f:
                        f.write(token_data["refresh_token"])

                    if instance:
                        # Write instance variables to config dir
                        with open(get_instance_file(), "w") as f:
                            json.dump(customer_instance_data, f)

                    authenticated = True
                elif token_data["error"] not in ("authorization_pending", "slow_down"):
                    error = token_data.get(
                        "error_description",
                        "Error authenticating the user. Please wait 30s and try again.",
                    )
                    raise ValueError(error)
                else:
                    time.sleep(device_code_data["interval"])
    else:
        raise ValueError("Please logout of current instance with `mindgard logout`")


def logout() -> None:
    """
    Removes the user token
    """
    print(f"Clearing credentials stored at {get_token_file()}.")
    clear_token()

    if is_instance_set():
        print(f"Clearing credentials stored at {get_instance_file()}.")
        clear_instance()

    print("Logged out!")


# TODO: test
def validate_id_token(id_token: str, auth0_domain: str, auth0_client_id: str) -> None:
    """
    Verify the token and its precedence. Raises if the token is invalid.

    :param id_token: string
    """
    jwks_url = "https://{}/.well-known/jwks.json".format(auth0_domain)
    issuer = "https://{}/".format(auth0_domain)
    sv = AsymmetricSignatureVerifier(jwks_url)
    tv = TokenVerifier(signature_verifier=sv, issuer=issuer, audience=auth0_client_id)
    tv.verify(id_token)


def load_access_token() -> Optional[str]:
    """
    Reads refresh token from file or environment variable and returns a new access token
    Returns None if no refresh token is found
    """
    auth_configs = load_auth_config()

    refresh_token = os.environ.get("MINDGARD_API_KEY")
    if not refresh_token and os.path.exists(get_token_file()):
        with open(get_token_file(), "r") as f:
            refresh_token = f.read()

    if refresh_token:
        access_token = (
            requests.post(
                "https://{}/oauth/token".format(auth_configs.AUTH0_DOMAIN),
                data={
                    "grant_type": "refresh_token",
                    "client_id": auth_configs.AUTH0_CLIENT_ID,
                    "audience": auth_configs.AUTH0_AUDIENCE,
                    "refresh_token": refresh_token,
                },
            )
            .json()
            .get("access_token")
        )
        return cast(str, access_token)
    return None


T = TypeVar("T")


# TODO: improve typing definitions here
def require_auth(func: Callable[..., CliResponse]) -> Callable[..., CliResponse]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> CliResponse:
        access_token = load_access_token()
        if not access_token:
            print_to_stderr("\033[1;37mRun `mindgard login`\033[0;0m to authenticate.")
            exit(CliResponse(2).code())
        try:
            return func(*args, **kwargs, access_token=access_token)
        except requests.HTTPError as e:
            if "Unauthorized" in str(e):
                print_to_stderr(
                    "Access token is invalid. Please re-authenticate using `mindgard login`"
                )
                clear_token()
                exit(CliResponse(2).code())
            else:
                raise e

    return wrapper
