# Exceptions
from typing import Tuple
from .exceptions import Uncontactable, HTTPBaseError

# Models
from .wrappers.llm import LLMModelWrapper

# UI
from rich.console import Console

# Logging
import logging


def preflight_llm(
    model_wrapper: LLMModelWrapper,
    console: Console,
    json_out: bool,
) -> bool:
    """
    Makes requests to the LLM to validate basic connectivity before submitting
    test.

    Returns True on success, False on failure
    """
    try:
        if not json_out:
            console.print("[white]Contacting model...")
        for i in range(5):
            _ = model_wrapper.__call__("Hello llm, are you there?")
        return True
    except Uncontactable as cerr:
        logging.debug(cerr)
        model_api = (
            model_wrapper.api_url if hasattr(model_wrapper, "api_url") else "<unknown>"
        )
        if not json_out:
            console.print(
                f"[red]Could not connect to the model! [white](URL: {model_api}, are you sure it's correct?)"
            )
    except HTTPBaseError as httpbe:
        logging.debug(httpbe)
        message: str = (
            f"[red]Model pre-flight check returned {httpbe.status_code} ({httpbe.status_message})"
        )
        if not json_out:
            console.print(message)
    except Exception as e:
        # something we've not really accounted for caught
        logging.error(e)
        raise e

    return False
