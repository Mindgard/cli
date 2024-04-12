

import argparse
import sys
import traceback
from typing import List, cast
from .error import ExpectedError
import toml

from .wrappers import get_model_wrapper

from .api_service import ApiService
from .list_tests_command import ListTestsCommand
from .run_test_command import RunTestCommand
from .llm_test_command import LLMTestCommand

from .attacks import get_attacks

from .auth import login
from .constants import VERSION
from .utils import is_version_outdated, print_to_stderr


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}", help='Show the current version number')

    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('login', help='Login to the Mindgard platform')

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
    list_attack_parser = list_subparsers.add_parser('attacks', help='List attacks')
    list_attack_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    list_attack_parser.add_argument('--id', type=str, help='Get the details of a specific attack.', required=False)

    # For testing purposes
    test_parser = subparsers.add_parser('test', help='Attack commands')
    test_parser.add_argument('target', nargs='?', type=str)
    test_parser.add_argument('--config-file', type=str, help='Path to mindgard.toml config file', default=None, required=False)
    test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)
    test_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    test_parser.add_argument('--headers', type=str, help='The headers to use', required=False)
    test_parser.add_argument('--preset', type=str, help='The preset to use', choices=['huggingface', 'openai', 'anthropic', 'custom_mistral'], required=False)
    test_parser.add_argument('--api-key', type=str, help='Specify the API key for the wrapper', required=False)
    test_parser.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    test_parser.add_argument('--model-name', type=str, help='Specify which model to run against (OpenAI and Anthropic)', required=False)
    test_parser.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    test_parser.add_argument('--system-prompt', type=str, help='Text file containing system prompt to use.', required=False)
    test_parser.add_argument('--selector', type=str, help='The selector to retrieve the text response from the LLM response JSON.', required=False)
    test_parser.add_argument('--request-template', type=str, help='The template to wrap the API request in.', required=False)

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
    elif args.command == 'list':
        if args.list_command == 'tests':
            api_service = ApiService()
            cmd = ListTestsCommand(api_service)
            res = cmd.run(json_format=bool(args.json), test_id=args.id)
            exit(res.code())
        elif args.list_command == 'attacks':
            res = get_attacks(json_format=args.json, attack_id=args.id)
            exit(res.code())
        else:
            print_to_stderr('Hey give us a command. Use `list tests` or `list attacks`.')
    elif args.command == 'sandbox':
        api_service = ApiService()
        cmd = RunTestCommand(api_service)
        res = cmd.run(model_name=args.target, json_format=bool(args.json), risk_threshold=int(args.risk_threshold))
        exit(res.code())
    elif args.command == 'attacks':
        res = get_attacks(json_format=args.json, attack_id=args.id)
        exit(res.code())
    elif args.command == 'test':
        # load args from file mindgard.toml
        config_file = args.config_file or "mindgard.toml"
        toml_args = {}
        try:
            with open(config_file, 'r') as f:
                contents = f.read()
                toml_args = toml.loads(contents)
        except FileNotFoundError as e:
            if args.config_file is None:
                pass
            else:
                raise e

        final_args = {k: v or toml_args.get(k) for k, v in vars(args).items()}

        # TODO: add a check for required args
        model_wrapper = get_model_wrapper(
            preset=final_args["preset"],
            headers_string=final_args["headers"],
            api_key=final_args["api_key"],
            url=final_args["url"],
            selector=final_args["selector"],
            request_template=final_args["request_template"],
            system_prompt=final_args["system_prompt"],
            model_name=final_args["model_name"]
        )

        api_service = ApiService()
        cmd = LLMTestCommand(api_service=api_service, model_wrapper=model_wrapper)
        res = cmd.run(target=final_args["target"], json_format=bool(final_args["json"]), risk_threshold=int(cast(str, final_args["risk_threshold"])))
        exit(res.code())
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
