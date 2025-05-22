import csv
import time
import requests
from rich.console import Console
from mindgard.auth import require_auth
from mindgard.constants import VERSION, API_BASE, EXIT_CODE_ERROR
from pathlib import Path
from dataclasses import dataclass
import logging

from mindgard.utils import print_to_stderr

console = Console()


class CreateDatasetError(Exception):
    pass


class InternalError(CreateDatasetError):
    pass


class UnauthorizedError(CreateDatasetError):
    pass


@dataclass
class CreateCustomDatasetRequest:
    seed_prompt: str
    perspective: str
    tone: str
    num_entries: int


@dataclass()
class CreateCustomDatasetCLIArgs:
    seed_prompt: str
    perspective: str
    tone: str
    output_filename: str
    num_entries: int


@require_auth
def create_custom_dataset(create_args: CreateCustomDatasetCLIArgs, access_token: str) -> None:
    """
    Create request to generate a custom dataset
    """
    url = f"{API_BASE}/dataset-generation"
    if Path(create_args.output_filename).exists():
        print_to_stderr(FileExistsError(
            f"File name: {create_args.output_filename} already exists. Please choose a different name by setting --output-filename <your_file_name>"))
        exit(EXIT_CODE_ERROR)

    if create_args.num_entries < 1 or create_args.num_entries > 250:
        print_to_stderr(
            ValueError(f"Number of entries (--num_entries) must be between 1 and 250 (provided: {create_args.num_entries})")
        )
        exit(EXIT_CODE_ERROR)

    try:

        json_payload = CreateCustomDatasetRequest(
            seed_prompt=create_args.seed_prompt,
            perspective=create_args.perspective,
            tone=create_args.tone,
            num_entries=create_args.num_entries
        ).__dict__

        logging.debug(f"Dataset generation request payload: {json_payload}")
        response = requests.post(
            url=url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": f"mindgard-cli/{VERSION}",
                "X-User-Agent": f"mindgard-cli/{VERSION}",
                "Content-Type": "application/json",
            },
            json=json_payload
        )
        if response.status_code == 201:
            with console.status("Dataset generation in progress...", spinner="dots"):
                logging.debug(f"Dataset generation started with request ID: {response.json()['id']}")
                while True:
                    time.sleep(0.5)
                    datasets = get_generated_dataset(dataset_id=response.json()["id"],
                                                     file_name=create_args.output_filename)
                    if datasets and datasets.get("is_complete", False):
                        console.print(f"Dataset generation completed. Filename is {create_args.output_filename}")
                        break
        response.raise_for_status()
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            raise UnauthorizedError("Invalid access token") from e
        elif e.response.status_code == 403:
            raise UnauthorizedError("Access denied") from e
        else:
            raise InternalError("An unexpected error occurred while creating dataset generation request") from e
    except Exception as e:
        raise InternalError("An unexpected error occurred creating dataset generation request") from e


@require_auth
def get_generated_dataset(dataset_id: str, access_token: str, file_name: str) -> None:
    """
    Get the generated dataset
    """
    url = f"{API_BASE}/dataset-generation/{dataset_id}"

    try:
        response = requests.get(
            url=url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": f"mindgard-cli/{VERSION}",
                "X-User-Agent": f"mindgard-cli/{VERSION}",
                "Content-Type": "application/json",
            },
        )
        if response.status_code == 200:
            with open(f"{file_name}", "w", newline='') as f:
                writer = csv.writer(f)
                for item in response.json()['items']:
                    writer.writerow([item])

        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            raise UnauthorizedError("Invalid access token") from e
        elif e.response.status_code == 403:
            raise UnauthorizedError("Access denied") from e
        else:
            raise InternalError("An unexpected error occurred while fetching generated dataset") from e
    except Exception as e:
        raise InternalError("An unexpected error occurred fetching generated dataset") from e
