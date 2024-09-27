from unittest.mock import MagicMock
from mindgard.throttle import throttle
def test_throttler() -> None:
    class Clock(object):
        def __init__(self):
            self.reset()

        def __call__(self):
            return self.now

        def reset(self):
            self.now = 0

        def increment(self, num:int=1):
            self.now += num

    clock = Clock()

    class Sleeper:
        calls:int = 0
        last_duration:int = 0
        def __call__(self, duration: int) -> None:
            self.last_duration = duration
            self.calls = self.calls + 1
            clock.increment(10)

    sleeper = Sleeper()

    mock_fn = MagicMock()
    throttled = throttle(f=mock_fn, clock=clock, sleeper=sleeper, rate_limit=1)
    
    throttled("first") # should return unthrottled
    assert mock_fn.call_count == 1, "wrapped function should not be repeatedly called"
    assert mock_fn.call_args[0][0] == "first"
    assert sleeper.calls == 0

    throttled("second") # should return after being throttled
    assert sleeper.calls == 6
    assert mock_fn.call_count == 2, "wrapped function should not be repeatedly called"
    assert mock_fn.call_args[0][0] == "second"