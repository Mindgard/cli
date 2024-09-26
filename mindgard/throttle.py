import time
from typing import Any, Callable, ParamSpec, TypeVar
from ratelimit import RateLimitException, limits

P = ParamSpec("P")
R = TypeVar('R')

def throttle(
        f:Callable[P, R], 
        rate_limit:int, 
        sleeper:Callable[[int], None]=time.sleep, 
        clock:Callable[[], float]=time.monotonic
) -> Callable[P, R]:
    """
    Throttle a function to a maximum number of calls per minute.

    Operates on a tumbling window of 60 seconds, during which if
    `rate_limit` is reached, the call is delayed until the window resets.

    Warning: this will release all throttled calls at once after the window resets.

    Args:
        f: the function (call-able) to throttle
        rate_limit: The number of calls allowed per minute
        sleeper: A sleep(n) compatible implementation [optional]
        clock: A time.monotonic() compatible implementation [optional]
    """
    ratelimited = limits(calls=rate_limit, clock=clock, period=60) 

    def wrapper(*args:Any, **kwargs:Any) -> R:
        while True:
            try:
                return ratelimited(f)(*args,**kwargs)
            except RateLimitException as exception:
                # loop once the window resets
                sleeper(int(exception.period_remaining))  # type: ignore # there is no type on the received exception from lib

    return wrapper