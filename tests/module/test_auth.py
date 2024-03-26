import os
import tempfile
from unittest import mock
from ...src.mindgard.auth import get_config_directory, clear_token, get_token_file, load_access_token


def test_config_location():
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            assert get_config_directory() == tmpdir
    with mock.patch.dict(os.environ, {}, clear=True):
        assert get_config_directory() == os.path.join(os.path.expanduser('~'), '.mindgard')


def test_token_clearing():
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            token_file = get_token_file()
            with open(token_file, 'w') as f:
                f.write('test token')
            assert os.path.exists(token_file)
            clear_token()
            assert not os.path.exists(token_file)


def test_token_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            token_file = get_token_file()
            with open(token_file, 'w') as f:
                f.write('test token')
            assert os.path.exists(token_file)
            assert 'test token' == load_access_token()
            clear_token()
            assert not os.path.exists(token_file)
            assert load_access_token() is None

