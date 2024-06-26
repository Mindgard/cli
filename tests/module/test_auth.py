import os
import tempfile
from unittest import mock
import requests_mock

from ...src.mindgard.constants import AUTH0_DOMAIN

from ...src.mindgard.auth import (clear_token, get_config_directory,
                                  get_token_file, load_access_token, logout)


def test_config_location() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            assert get_config_directory() == tmpdir
    with mock.patch.dict(os.environ, {}, clear=True):
        assert get_config_directory() == os.path.join(os.path.expanduser('~'), '.mindgard')


def test_token_clearing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            token_file = get_token_file()
            with open(token_file, 'w') as f:
                f.write('test token')
            assert os.path.exists(token_file)
            clear_token()
            assert not os.path.exists(token_file)


def test_logout() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            token_file = get_token_file()
            with open(token_file, 'w') as f:
                f.write('test token')
            assert os.path.exists(token_file)
            logout()
            assert not os.path.exists(token_file)


def test_token_load(requests_mock: requests_mock.Mocker) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            token_file = get_token_file()
            with open(token_file, 'w') as f:
                f.write('test token')
            assert os.path.exists(token_file)

            requests_mock.post(
                'https://{}/oauth/token'.format(AUTH0_DOMAIN), 
                json={'access_token': 'test token'}
            )
            assert 'test token' == load_access_token()

            clear_token()
            assert not os.path.exists(token_file)
            assert load_access_token() is None

def test_token_load_env_vars(requests_mock: requests_mock.Mocker) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):

            assert None == load_access_token()

            with mock.patch.dict(os.environ, {"MINDGARD_API_KEY": "test token"}):
                requests_mock.post(
                    'https://{}/oauth/token'.format(AUTH0_DOMAIN), 
                    json={'access_token': 'test tokenasdf'}
                )
                assert 'test tokenasdf' == load_access_token()