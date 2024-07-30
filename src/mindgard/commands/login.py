from ..auth import (
    is_instance_set,
    sandbox_auth_config,
    instance_auth_config,
    validate_id_token,
    create_config_directory,
    get_token_file,
    get_instance_file,
    clear_token,
    clear_instance,
)
import requests
from ..utils import print_to_stderr

from rich.console import Console

import json
import time


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
