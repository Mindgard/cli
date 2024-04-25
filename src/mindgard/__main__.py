

import argparse
import sys
import traceback
from typing import List, cast
from .error import ExpectedError

from .list_tests_command import ListTestsCommand
from .run_test_command import RunTestCommand
from .llm_test_command import LLMTestCommand
from .run_llm_local_command import RunLLMLocalCommand

from .api_service import ApiService

from .auth import login, logout
from .constants import VERSION
from .utils import is_version_outdated, print_to_stderr, parse_args_into_model, parse_toml_and_args_into_final_args


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}", help='Show the current version number')

    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('login', help='Login to the Mindgard platform')
    subparsers.add_parser('logout', help='Logout of the Mindgard platform in the CLI')

    # TODO: better error message if someone provides an id that is for the wrong resource eg attacks or tests
    attack_parser = subparsers.add_parser('attacks', help='See the attacks you\'ve run.')  # TODO: alias single version of plural nouns
    attack_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    attack_parser.add_argument('--id', type=str, help='Get the details of a specific attack.', required=False)

    sandbox_test_parser = subparsers.add_parser('sandbox', help='Test a mindgard example model')
    sandbox_test_parser.add_argument('target', nargs='?', type=str, choices=['cfp_faces', 'mistral'])
    sandbox_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    sandbox_test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)

    list_parser = subparsers.add_parser('list', help='List items')
    list_subparsers = list_parser.add_subparsers(dest='list_command')
    list_test_parser = list_subparsers.add_parser('tests', help='List tests')
    list_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    list_test_parser.add_argument('--id', type=str, help='Get the details of a specific test.', required=False)

    # For testing purposes
    test_parser = subparsers.add_parser('test', help='Attack commands')
    test_parser.add_argument('target', nargs='?', type=str)
    test_parser.add_argument('--config-file', type=str, help='Path to mindgard.toml config file', default=None, required=False)
    test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)
    test_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    test_parser.add_argument('--headers', type=str, help='The headers to use', required=False)
    test_parser.add_argument('--preset', type=str, help='The preset to use', choices=['huggingface', 'openai', 'anthropic', 'custom_mistral', 'tester'], required=False)
    test_parser.add_argument('--api-key', type=str, help='Specify the API key for the wrapper', required=False)
    test_parser.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    test_parser.add_argument('--model-name', type=str, help='Specify which model to run against (OpenAI and Anthropic)', required=False)
    test_parser.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    test_parser.add_argument('--system-prompt', type=str, help='Text file containing system prompt to use.', required=False)
    test_parser.add_argument('--selector', type=str, help='The selector to retrieve the text response from the LLM response JSON.', required=False)
    test_parser.add_argument('--request-template', type=str, help='The template to wrap the API request in.', required=False)

    alpha_test_parser = subparsers.add_parser('alphatest', help='Attack commands')
    alpha_test_parser.add_argument('target', nargs='?', type=str)
    alpha_test_parser.add_argument('--config-file', type=str, help='Path to mindgard.toml config file', default=None, required=False)
    alpha_test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)
    alpha_test_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    alpha_test_parser.add_argument('--headers', type=str, help='The headers to use', required=False)
    alpha_test_parser.add_argument('--preset', type=str, help='The preset to use', choices=['huggingface', 'openai', 'anthropic', 'custom_mistral'], required=False)
    alpha_test_parser.add_argument('--api-key', type=str, help='Specify the API key for the wrapper', required=False)
    alpha_test_parser.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    alpha_test_parser.add_argument('--model-name', type=str, help='Specify which model to run against (OpenAI and Anthropic)', required=False)
    alpha_test_parser.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    alpha_test_parser.add_argument('--system-prompt', type=str, help='Text file containing system prompt to use.', required=False)
    alpha_test_parser.add_argument('--selector', type=str, help='The selector to retrieve the text response from the LLM response JSON.', required=False)
    alpha_test_parser.add_argument('--request-template', type=str, help='The template to wrap the API request in.', required=False)

    return parser.parse_args(args)


def main() -> None:
    args = parse_args(sys.argv[1:])

    if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
        print_to_stderr("Python 3.8 or later is required to run the Mindgard CLI.")
        sys.exit(1)

    if new_version := is_version_outdated():
        print_to_stderr(f"New version available: {new_version}. Run 'pip install mindgard --upgrade' to upgrade. Older versions of the CLI may not be actively maintained.")

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
            print_to_stderr('Provide a resource to list. Eg `list tests` or `list attacks`.')
    elif args.command == 'sandbox':
        api_service = ApiService()
        run_test_cmd = RunTestCommand(api_service)
        run_test_res = run_test_cmd.run(model_name=args.target, json_format=bool(args.json), risk_threshold=int(args.risk_threshold))
        exit(run_test_res.code())
    elif args.command == "alphatest":
        # load args from file mindgard.toml
        final_args = parse_toml_and_args_into_final_args(args.config_file, args)
        model_wrapper = parse_args_into_model(final_args)
        api_service = ApiService()
        llm_test_cmd = RunLLMLocalCommand(api_service=api_service, model_wrapper=model_wrapper)
        llm_test_res = llm_test_cmd.run(target=final_args["target"], json_format=bool(final_args["json"]), risk_threshold=int(cast(str, final_args["risk_threshold"])))
    elif args.command == 'test':
        # load args from file mindgard.toml
        final_args = parse_toml_and_args_into_final_args(args.config_file, args)
        model_wrapper = parse_args_into_model(final_args)
        api_service = ApiService()
        llm_test_cmd = LLMTestCommand(api_service=api_service, model_wrapper=model_wrapper)
        llm_test_res = llm_test_cmd.run(target=final_args["target"], json_format=bool(final_args["json"]), risk_threshold=int(cast(str, final_args["risk_threshold"])))
        exit(llm_test_res.code())
    else:
        print_to_stderr('Which command are you looking for? See: $ mindgard --help')


if __name__ == '__main__':
    try:
        main()
    except ExpectedError as e:
        print_to_stderr(str(e))
        exit(2)
    except Exception:
        traceback.print_exc()
        exit(2)
