import subprocess


def test_cli_on_path() -> None:
    result = subprocess.run(['mindgard', '-h'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'usage: mindgard [command] [options]' in result.stdout


def test_cli_help() -> None:
    result = subprocess.run(['python3', '-m', 'mindgard', '-h'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'usage: mindgard [command] [options]' in result.stdout


def test_cli_attackcategories() -> None:
    result = subprocess.run(['python3', '-m', 'mindgard', 'attackcategories'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'First authenticate with Mindgard API.' in result.stderr


def test_cli_auth() -> None:
    try:
        subprocess.run(['python3', '-m', 'mindgard', 'auth'], capture_output=True, text=True, timeout=1)
    except subprocess.TimeoutExpired as e:
        assert e.stdout
        assert 'Welcome to Mindgard! Let\'s get you authenticated...' in str(e.stdout)
        assert 'Register/log in using the web UI.' not in str(e.stdout)
    else:
        # If no timeout occurred, fail the test
        assert False, "Expected auth call to timeout because it expects user action, but it didn't."