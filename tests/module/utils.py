import contextlib
import io
import sys
from typing import Generator, Tuple


@contextlib.contextmanager
def suppress_output() -> Generator[Tuple[io.StringIO, io.StringIO], None, None]:
    new_out, new_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err