

import argparse
import sys
from typing import List

from .attacks import attackcategories, get_attacks

from .auth import login
from .constants import VERSION
from .tests import get_tests, run_test
from .utils import is_version_outdated, print_to_stderr


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Securing AIs', prog='mindgard', usage='%(prog)s [command] [options]', epilog='Enjoy the program! :)', add_help=True)
    parser.add_argument('--version', action='version', version=f"%(prog)s {VERSION}", help='Show the current version number')

    subparsers = parser.add_subparsers(dest='command', title='commands', description='Use these commands to interact with the Mindgard API')

    attack_categories_parser = subparsers.add_parser('attackcategories', help='Get a list of attack categories.')
    attack_categories_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.') 

    subparsers.add_parser('login', help='Login to the Mindgard platform')

    # TODO: think about more streamlined command for running a test
    test_parser = subparsers.add_parser('tests', help='See the tests you\'ve run.') # TODO: better help text
    test_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False) # TODO: don't allow this if run comes after
    test_parser.add_argument('--id', type=str, help='Get the details of a specific test.', required=False)
    
    test_subparsers = test_parser.add_subparsers(dest='test_commands', title='test_commands', description='Perform actions against tests')
    test_run_parser = test_subparsers.add_parser('run', help='Run a test.') # TODO: risk exit codes
    # TODO: links to view results in the UI for images etc
    test_run_parser.add_argument('--name', type=str, help='The attack to tests.', required=True, choices=['cfp_faces', 'mistral'])
    test_run_parser.add_argument('--json', action="store_true", help='Initiate test and return id that can be used to check status.', required=False)
    test_run_parser.add_argument('--risk-threshold', type=int, help='Set a risk threshold above which the system will exit 1', required=False, default=80)

    # TODO: better error message if someone provides an id that is for the wrong resource eg attacks or tests
    attack_parser = subparsers.add_parser('attacks', help='See the attacks you\'ve run.') # TODO: alias single version of plural nouns
    attack_parser.add_argument('--json', action="store_true", help='Output the info in JSON format.', required=False)
    attack_parser.add_argument('--id', type=str, help='Get the details of a specific attack.', required=False)

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
    elif args.command == 'attackcategories':
        res = attackcategories(json_format=args.json)
        exit(res.code())
    elif args.command == 'tests':
        if args.test_commands == "run":
            res = run_test(attack_name=args.name, json_format=bool(args.json), risk_threshold=int(args.risk_threshold))
            exit(res.code())
        else:
            res = get_tests(json_format=bool(args.json), test_id=args.id)
            exit(res.code())
    elif args.command == 'attacks':
        res = get_attacks(json_format=args.json, attack_id=args.id)
        exit(res.code())
    else:
        print_to_stderr('Hey give us a command. Use list or auth.') # TODO update


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print_to_stderr(e)
        exit(2)