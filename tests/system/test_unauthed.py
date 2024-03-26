import subprocess


def test_cli_help():
    result = subprocess.run(['python3', '-m', 'mindgard', '-h'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'usage: mindgard [command] [options]' in result.stdout


def test_cli_list():
    result = subprocess.run(['python3', '-m', 'mindgard', 'attackcategories'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'First authenticate with Mindgard API.' in result.stdout


def test_cli_auth():
    try:
        subprocess.run(['python3', '-m', 'mindgard', 'auth'], capture_output=True, text=True, timeout=1)
    except subprocess.TimeoutExpired as e:
        # Check stdout if available
        if hasattr(e, 'stdout') and e.stdout:
            assert 'Welcome to Mindgard! Let\'s get you authenticated...' in e.stdout
            assert 'Register/log in using the web UI.' not in e.stdout
    else:
        # If no timeout occurred, fail the test
        assert False, "Expected auth call to timeout because it expects user action, but it didn't."