import argparse
import textwrap
import os
import sys
import traceback

# Types
from typing import List, cast

from mindgard.types import log_levels, type_model_presets_list, valid_llm_datasets

# Models
from mindgard.preflight import preflight_llm
from mindgard.wrappers.utils import parse_args_into_model
from mindgard.wrappers.llm import LLMModelWrapper

# Run functions
from mindgard.run_functions.list_tests import list_test_submit, list_test_polling, list_test_output
from mindgard.run_functions.sandbox_test import submit_sandbox_submit_factory, submit_sandbox_polling
from mindgard.run_functions.external_models import model_test_polling, model_test_output_factory, model_test_submit_factory
from mindgard.external_model_handlers.llm_model import llm_message_handler
from mindgard.run_poll_display import cli_run

from mindgard.orchestrator import OrchestratorSetupRequest

# Constants and Utils
from mindgard.constants import VERSION
from mindgard.utils import is_version_outdated, print_to_stderr, parse_toml_and_args_into_final_args, convert_test_to_cli_response, CliResponse

# Logging
import logging
from rich.logging import RichHandler
from rich.console import Console

# Auth
from mindgard.auth import login, logout

# both validate and test need these same arguments, so have factored them out
def shared_arguments(parser: argparse.ArgumentParser):
    parser.add_argument('target', nargs='?', type=str, help="This is your own model identifier.")
    parser.add_argument('--config-file', type=str, help='Path to mindgard.toml config file', default=None, required=False)
    parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False, default=False)
    parser.add_argument('--headers', type=str, help='The headers to use. Comma separated list.', required=False)
    parser.add_argument('--header', type=str, help='The headers to use, repeat flag for each header.', action='append', required=False)
    parser.add_argument('--preset', type=str, help='The preset to use', choices=type_model_presets_list, required=False)
    parser.add_argument('--api-key', type=str, help='Specify the API key for the wrapper', required=False)
    parser.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    parser.add_argument('--model-name', type=str, help='Specify which model to run against (OpenAI and Anthropic)', required=False)
    parser.add_argument('--az-api-version', type=str, help='Specify the Azure OpenAI API version (Azure only)', required=False)
    parser.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    parser.add_argument('--system-prompt', type=str, help='Text file containing system prompt to use.', required=False)
    parser.add_argument('--selector', type=str, help='The selector to retrieve the text response from the LLM response JSON.', required=False)
    parser.add_argument('--request-template', type=str, help='The template to wrap the API request in.', required=False)
    parser.add_argument('--tokenizer', type=str, help='Choose a HuggingFace model to provide a tokeniser for prompt and chat completion templating.', required=False)
    parser.add_argument('--risk-threshold', type=int, help='Set a flagged event to total event ratio threshold above which the system will exit 1', required=False)

def parse_args(args: List[str]) -> argparse.Namespace:
    default_log_level = 'warn'

    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}", help='Show the current version number')
    parser.add_argument('--log-level', type=str, help='Specify the output verbosity', choices=log_levels, required=False, default=default_log_level)

    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    login_parser = subparsers.add_parser('login', help='Login to the Mindgard platform')
    login_parser.add_argument('--instance', nargs='?', type=str, help='Point to your deployed Mindgard instance. If not provided, cli will point towards Mindgard Sandbox')
    
    subparsers.add_parser('logout', help='Logout of the Mindgard platform in the CLI')

    sandbox_test_parser = subparsers.add_parser('sandbox', help='Test a mindgard example model')
    sandbox_test_parser.add_argument('target', nargs='?', type=str, choices=['cfp_faces', 'mistral'], default="cfp_faces")
    sandbox_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    sandbox_test_parser.add_argument('--risk-threshold', type=int, help='Set a flagged event to total event ratio threshold above which the system will exit 1', required=False, default=80)

    list_parser = subparsers.add_parser('list', help='List items')
    list_subparsers = list_parser.add_subparsers(dest='list_command')
    list_test_parser = list_subparsers.add_parser('tests', help='List tests')
    list_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    list_test_parser.add_argument('--id', type=str, help='Get the details of a specific test.', required=False)

    test_parser = subparsers.add_parser("test", help="Attacks command", formatter_class=argparse.RawTextHelpFormatter)
    shared_arguments(test_parser)
    test_parser.add_argument('--parallelism', type=int, help='The maximum number of parallel requests that can be made to the API.', required=False)
    test_parser.add_argument('--rate-limit', type=int, help='The maximum number of requests to make to model in one minute (default: 3600)', required=False)
    test_parser.add_argument('--force-multi-turn', type=bool, help='Enable multi turn attacks in scenarios where they may not be safe, such as when testing an API without chat completions history.', required=False)
    test_parser.add_argument('--dataset', type=str, help=textwrap.dedent(f'''
                                                                         The dataset to be used for running the attacks on the given model.
                                                                         This should be a csv formatted file path, with each prompt on a new line'''), required=False)
    test_parser.add_argument('--domain', type=str, help='The domain to inform the dataset used for LLMs.', choices=valid_llm_datasets, required=False)
    test_parser.add_argument('--mode', type=str, help='Specify the number of samples to use during attacks; contact Mindgard for access to \'thorough\' or \'exhaustive\' test', choices=['fast', 'thorough', 'exhaustive'], required=False)
    test_parser.add_argument('--exclude', type=str, help=textwrap.dedent(f'''
                                                                         Exclude certain attacks from the test. Exclusions can be done either by name or category.
                                                                         The supported attacks can be found here - https://docs.mindgard.ai/user-guide/running-subset-of-attacks#list-of-attacks'''), action='append',required=False)
    test_parser.add_argument('--include', type=str, help=textwrap.dedent(f'''
                                                                         Include a selected set of attacks in the test. A name or category can be provided as part of the inclusion. 
                                                                         The supported attacks can be found here - https://docs.mindgard.ai/user-guide/running-subset-of-attacks#list-of-attacks'''), action='append',required=False)
    test_parser.add_argument('--prompt-repeats', type=int, help='The number of times to repeat the prompt for each sample in the dataset.', required=False)
    

    validate_parser = subparsers.add_parser("validate", help="Validates that we can communicate with your model")
    shared_arguments(validate_parser)

    return parser.parse_args(args)

def run_cli() -> None:
    args = parse_args(sys.argv[1:])

    FORMAT = "%(message)s"
    logging.basicConfig(
        level=args.log_level.upper(), format=FORMAT, datefmt="[%X]", handlers=[RichHandler(console=Console(stderr=True),locals_max_string=None,locals_max_length=None)]
    )

    if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
        print_to_stderr("Python 3.8 or later is required to run the Mindgard CLI.")
        sys.exit(2)

    if new_version := is_version_outdated():
        print_to_stderr(f"New version available: {new_version}. Please upgrade as older versions of the CLI may not be actively maintained.")

    if args.command == 'login':
        login(instance=args.instance)
    elif args.command == 'logout':
        logout()
    elif args.command == 'list':
        if args.list_command == 'tests':
            cli_run(submit_func=list_test_submit, polling_func=list_test_polling, output_func=list_test_output, json_out=args.json, submitting_text="Fetching tests...")
            exit(CliResponse(0).code())
        else:
            print_to_stderr('Provide a resource to list. Eg `list tests`.')
    elif args.command == 'sandbox':
        submit_sandbox_submit = submit_sandbox_submit_factory(model_name=args.target)
        submit_sandbox_output = model_test_output_factory(risk_threshold=100)

        cli_response = cli_run(submit_func=submit_sandbox_submit, polling_func=submit_sandbox_polling, output_func=submit_sandbox_output, json_out=args.json)
        exit(convert_test_to_cli_response(test=cli_response, risk_threshold=100).code())

    elif args.command == "validate" or args.command == "test":
        console = Console()
        final_args = parse_toml_and_args_into_final_args(args.config_file, args)
        model_wrapper = parse_args_into_model(final_args)

        passed_preflight = preflight_llm(model_wrapper, console=console, json_out=final_args["json"])

        if not final_args["json"]:
            console.print(f"{'[green bold]Model contactable!' if passed_preflight else '[red bold]Model not contactable!'}")


        if passed_preflight:
            if args.command == 'test':
                if os.getenv("MINDGARD_TOGGLE_USE_LIB") == "true":
                    from mindgard.main_lib import run_test
                    run_test(final_args, model_wrapper)
                else:
                    request = OrchestratorSetupRequest(
                        target=final_args["target"],
                        parallelism=final_args["parallelism"],
                        system_prompt=final_args["system_prompt"],
                        dataset=final_args.get("custom_dataset", final_args["dataset"]),
                        custom_dataset=final_args.get("custom_dataset",None),
                        modelType="llm",
                        attackSource="user",
                        attackPack=final_args["attack_pack"],
                        exclude=final_args["exclude"],
                        include=final_args["include"],
                        prompt_repeats=final_args["prompt_repeats"],
                    )
                    submit = model_test_submit_factory(
                        request=request,
                        model_wrapper=cast(LLMModelWrapper, model_wrapper),
                        message_handler=llm_message_handler
                    )

                    output = model_test_output_factory(risk_threshold=int(final_args["risk_threshold"]))
                    cli_response = cli_run(submit, model_test_polling, output_func=output, json_out=final_args["json"])
                    exit(convert_test_to_cli_response(test=cli_response, risk_threshold=int(final_args["risk_threshold"])).code()) # type: ignore

        else:
            exit(CliResponse(1).code())
        
    else:
        print_to_stderr('Which command are you looking for? See: $ mindgard --help')


def main() -> None:
    try:
        run_cli()
    except ValueError as e:
        print_to_stderr(str(e))
        exit(2)
    except Exception:
        traceback.print_exc()
        exit(2)