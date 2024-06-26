

import argparse
from argparse import ArgumentParser
import sys
import traceback
from typing import List, cast, Any

from .wrappers import parse_args_into_model

from .utils import CliResponse

from .list_tests_command import ListTestsCommand
from .run_test_command import RunTestCommand
from .run_llm_local_command import RunLLMLocalCommand

from .preflight import preflight

from .api_service import ApiService

from .auth import login, logout
from .constants import VERSION
from .utils import is_version_outdated, print_to_stderr, parse_toml_and_args_into_final_args

import logging
from rich.logging import RichHandler
from rich.console import Console


# both validate and test need these same arguments, so have factored them out
def subparser_for_llm_contact(command_str: str, description_str: str, argparser: Any) -> ArgumentParser:
    parser: ArgumentParser = argparser.add_parser(command_str, help=description_str)
    parser.add_argument('target', nargs='?', type=str, help="This is your own model identifier.")
    parser.add_argument('--config-file', type=str, help='Path to mindgard.toml config file', default=None, required=False)
    parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    parser.add_argument('--headers', type=str, help='The headers to use', required=False)
    parser.add_argument('--preset', type=str, help='The preset to use', choices=['huggingface', 'openai', 'anthropic', 'azure-openai', 'azure-aistudio', 'custom_mistral', 'tester'], required=False)
    parser.add_argument('--api-key', type=str, help='Specify the API key for the wrapper', required=False)
    parser.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    parser.add_argument('--model-name', type=str, help='Specify which model to run against (OpenAI and Anthropic)', required=False)
    parser.add_argument('--az-api-version', type=str, help='Specify the Azure OpenAI API version (Azure only)', required=False)
    parser.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    parser.add_argument('--system-prompt', type=str, help='Text file containing system prompt to use.', required=False)
    parser.add_argument('--selector', type=str, help='The selector to retrieve the text response from the LLM response JSON.', required=False)
    parser.add_argument('--request-template', type=str, help='The template to wrap the API request in.', required=False)
    parser.add_argument('--tokenizer', type=str, help='Choose a HuggingFace model to provide a tokeniser for prompt and chat completion templating.', required=False)

    return parser


def parse_args(args: List[str]) -> argparse.Namespace:
    log_levels = ['critical', 'fatal', 'error', 'warn', 'warning', 'info', 'debug', 'notset'] # [n.lower() for n in logging.getLevelNamesMapping().keys()]
    default_log_level = 'warn'

    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}", help='Show the current version number')
    parser.add_argument('--log-level', type=str, help='Specify the output verbosity', choices=log_levels, required=False, default=default_log_level)

    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('login', help='Login to the Mindgard platform')
    subparsers.add_parser('logout', help='Logout of the Mindgard platform in the CLI')

    sandbox_test_parser = subparsers.add_parser('sandbox', help='Test a mindgard example model')
    sandbox_test_parser.add_argument('target', nargs='?', type=str, choices=['cfp_faces', 'mistral'])
    sandbox_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    sandbox_test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)

    list_parser = subparsers.add_parser('list', help='List items')
    list_subparsers = list_parser.add_subparsers(dest='list_command')
    list_test_parser = list_subparsers.add_parser('tests', help='List tests')
    list_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    list_test_parser.add_argument('--id', type=str, help='Get the details of a specific test.', required=False)

    test_parser = subparser_for_llm_contact("test", "Attacks command", subparsers)
    test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)
    test_parser.add_argument('--parallelism', type=int, help='The maximum number of parallel requests that can be made to the API.', required=False, default=5)

    validate_parser = subparser_for_llm_contact("validate", "Validates that we can communicate with your model", subparsers)

    return parser.parse_args(args)


def main() -> None:
    args = parse_args(sys.argv[1:])

    FORMAT = "%(message)s"
    logging.basicConfig(
        level=args.log_level.upper(), format=FORMAT, datefmt="[%X]", handlers=[RichHandler(console=Console(stderr=True))]
    )

    if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
        print_to_stderr("Python 3.8 or later is required to run the Mindgard CLI.")
        sys.exit(2)

    if new_version := is_version_outdated():
        print_to_stderr(f"New version available: {new_version}. Please upgrade as older versions of the CLI may not be actively maintained.")

    if args.command == 'login':
        login()
    elif args.command == 'logout':
        logout()
    elif args.command == 'list':
        if args.list_command == 'tests':
            api_service = ApiService()
            cmd = ListTestsCommand(api_service)
            res = cmd.run(json_format=bool(args.json), test_id=args.id)
            exit(res.code())
        else:
            print_to_stderr('Provide a resource to list. Eg `list tests`.')
    elif args.command == 'sandbox':
        api_service = ApiService()
        run_test_cmd = RunTestCommand(api_service)
        run_test_res = run_test_cmd.run(model_name=args.target, json_format=bool(args.json), risk_threshold=int(args.risk_threshold))
        exit(run_test_res.code())
    if args.command == "validate" or args.command == "test":
        console = Console()
        final_args = parse_toml_and_args_into_final_args(args.config_file, args)
        model_wrapper = parse_args_into_model(final_args)
        passed:bool = preflight(model_wrapper, console=console)
        response = CliResponse(passed)

        console.print(f"{'[green bold]Model contactable!' if passed else '[red bold]Model not contactable!'}")

        if passed:
            if args.command == 'test':
                # load args from file mindgard.toml
                RunLLMLocalCommand.validate_args(final_args)
                api_service = ApiService()
                parallelism = int(cast(str, final_args["parallelism"]))
                llm_test_cmd = RunLLMLocalCommand(api_service=api_service, model_wrapper=model_wrapper, parallelism=parallelism)
                llm_test_res = llm_test_cmd.run(
                    target=final_args["target"], 
                    json_format=bool(final_args["json"]), 
                    risk_threshold=int(cast(str, final_args["risk_threshold"])), 
                    system_prompt=final_args["system_prompt"],
                    console=console
                )
                exit(llm_test_res.code())

        exit(response.code())
        
        
    else:
        print_to_stderr('Which command are you looking for? See: $ mindgard --help')


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print_to_stderr(str(e))
        exit(2)
    except Exception:
        traceback.print_exc()
        exit(2)
