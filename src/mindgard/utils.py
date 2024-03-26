import sys

def print_to_stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)