from ...src.mindgard.run_command import validate_kwargs


def test_kwargs_validation_pass() -> None:
    parameters = {
        "system_prompt": "Hello!"
    }
    assert validate_kwargs(parameters) is True


def test_kwargs_validation_fail() -> None:
    parameters = {
        "ahhhhhh": "Hello!"
    }
    assert validate_kwargs(parameters) is False


