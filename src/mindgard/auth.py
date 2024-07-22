import json
import os
import time
from typing import Any, Callable, Optional, TypeVar, cast
from functools import wraps

from rich.progress import Console

import requests
from auth0.authentication.token_verifier import (
    AsymmetricSignatureVerifier,  # type: ignore
    TokenVerifier,
)

from .utils import CliResponse, print_to_stderr
from .config import (
    get_token_file,
    get_instance_file,
    create_config_directory,
    load_auth_config,
    is_instance_set,
    instance_auth_config,
    sandbox_auth_config,
)


def clear_token() -> None:
    if os.path.exists(get_token_file()):
        os.remove(get_token_file())


def clear_instance() -> None:
    """
    Deletes the instance file
    """
    if os.path.exists(get_instance_file()):
        os.remove(get_instance_file())


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
            return CliResponse(2)
        try:
            return func(*args, **kwargs, access_token=access_token)
        except requests.HTTPError as e:
            if "Unauthorized" in str(e):
                print_to_stderr(
                    "Access token is invalid. Please re-authenticate using `mindgard login`"
                )
                clear_token()
                return CliResponse(2)
            else:
                raise e

    return wrapper
