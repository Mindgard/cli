

import argparse
import sys
from typing import List

from .template import Template

from .wrappers import run_attack, run_prompt

from .api_service import ApiService
from .list_tests_command import ListTestsCommand

from .attacks import get_attacks

from .auth import login
from .constants import VERSION
from .tests import get_tests, run_test
from .utils import is_version_outdated, print_to_stderr


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}", help='Show the current version number')

    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')
    subparsers.add_parser('login', help='Login to the Mindgard platform')

    # TODO: think about more streamlined command for running a test
    tests_parser = subparsers.add_parser('tests', help='See the tests you\'ve run.') # TODO: better help text
    tests_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False) # TODO: don't allow this if run comes after
    tests_parser.add_argument('--id', type=str, help='Get the details of a specific test.', required=False)
    
    tests_subparsers = tests_parser.add_subparsers(dest='test_commands', title='test_commands', description='Perform actions against tests')
    tests_run_parser = tests_subparsers.add_parser('run', help='Run a test.')
    
    # TODO: links to view results in the UI for images etc
    tests_run_parser.add_argument('--name', type=str, help='The attack to tests.', required=True, choices=['cfp_faces', 'mistral'])
    tests_run_parser.add_argument('--json', action="store_true", help='Initiate test and return id that can be used to check status.', required=False)
    tests_run_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)

    # TODO: better error message if someone provides an id that is for the wrong resource eg attacks or tests
    attack_parser = subparsers.add_parser('attacks', help='See the attacks you\'ve run.') # TODO: alias single version of plural nouns
    attack_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    attack_parser.add_argument('--id', type=str, help='Get the details of a specific attack.', required=False)

    # from here is new command structure which we're incrementally adding
    test_parser = subparsers.add_parser('test', help='Test a model')
    # since this feels nonsensical, here's a link: https://docs.python.org/3/library/argparse.html#nargs
    test_parser.add_argument('target', nargs='?', type=str)
    test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    test_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)

    list_parser = subparsers.add_parser('list', help='List items')
    list_subparsers = list_parser.add_subparsers(dest='list_command')
    list_test_parser = list_subparsers.add_parser('tests', help='List tests')
    list_test_parser.add_argument('--json', action="store_true", help='Return json output', required=False)
    list_test_parser.add_argument('--id', type=str, help='Get the details of a specific test.', required=False)

    # For testing purposes
    wrapper_parser = subparsers.add_parser('attack', help='Attack commands')
    wrapper_parser.add_argument('attack_name', nargs='?', type=str)
    wrapper_parser.add_argument('--headers', type=str, help='The headers to use', required=False)
    wrapper_parser.add_argument('--preset', type=str, help='The preset to use', choices=['huggingface', 'openai', 'anthropic', 'custom_mistral'], required=False)
    wrapper_parser.add_argument('--api_key', type=str, help='Specify the API key for the wrapper', required=False)
    wrapper_parser.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    wrapper_parser.add_argument('--model_name', type=str, help='Specify which model to run againist (OpenAI and Anthropic)', required=False)
    wrapper_parser.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    wrapper_parser.add_argument('--system_prompt', type=str, help='Text file containing system prompt to use.', required=False)
    wrapper_parser.add_argument('--selector', type=str, help='The selector to retrieve the text response from the LLM response JSON.', required=False)
    wrapper_parser.add_argument('--request_template', type=str, help='The template to wrap the API request in.', required=False)

    prompt_test = subparsers.add_parser('prompt', help='Attack commands')
    prompt_test.add_argument('--preset', type=str, help='The preset to use', choices=['huggingface', 'openai', 'anthropic', 'custom_mistral'], required=True)
    prompt_test.add_argument('--api_key', type=str, help='Specify the API key for the wrapper', required=False)
    prompt_test.add_argument('--url', type=str, help='Specify the url for the wrapper', required=False)
    prompt_test.add_argument('--model_name', type=str, help='Specify which model to run againist (OpenAI and Anthropic)', required=False)
    prompt_test.add_argument('--prompt', type=str, help='Specify the prompt to use', required=False)
    prompt_test.add_argument('--preset_template', type=str, help='Use a preset prompt template.', choices=Template.Models.__dir__(), required=False)
    prompt_test.add_argument('--system_prompt', type=str, help='Text file containing system prompt to use.', required=False)
    prompt_test.add_argument('--prompt_template', type=str, help='Specify own custom template.', required=False)
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
    elif args.command == 'list' and args.list_command == 'tests':
        api_service = ApiService()
        cmd = ListTestsCommand(api_service)
        res = cmd.run(json_format=bool(args.json), test_id=args.id)
        exit(res.code())
    elif args.command == 'test':
        if args.target is None:
            raise Exception("test command requires target argument")
        res = run_test(target_name=args.target, json_format=bool(args.json), risk_threshold=int(args.risk_threshold))
        exit(res.code())
    elif args.command == 'tests':
        if args.test_commands == "run":
            res = run_test(target_name=args.name, json_format=bool(args.json), risk_threshold=int(args.risk_threshold))
            exit(res.code())
        else:
            res = get_tests(json_format=bool(args.json), test_id=args.id)
            exit(res.code())
    elif args.command == 'attacks':
        res = get_attacks(json_format=args.json, attack_id=args.id)
        exit(res.code())
    elif args.command == 'attack':
        run_attack(preset=args.preset, headers_string=args.headers, attack_name=args.attack_name, api_key=args.api_key, url=args.url, selector=args.selector, request_template=args.request_template, system_prompt=args.system_prompt, model_name=args.model_name)
    elif args.command == 'prompt':
        run_prompt(**vars(args))
    else:
        print_to_stderr('Hey give us a command. Use list or auth.') # TODO update


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print_to_stderr(e)
        exit(2)