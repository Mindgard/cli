import json
import os
import tempfile
from unittest import mock
import requests_mock

from src.mindgard.auth import (clear_token, clear_instance, load_access_token, logout)
from src.mindgard.config import get_config_directory, get_token_file, get_instance_file, instance_auth_config, load_auth_config, sandbox_auth_config

def generate_instance_config() -> dict[str, str]:
     config = {
                "domain": "login.heyuser.mindgard.ai",
                "clientId": "i_am_client_id",
                "audience": "i_am_an_audience",
                "dashboardUrl": "i_am_dashboard_url",
                "apiBase": "i_am_api_base"
            }
     return config

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
            auth_configs = load_auth_config()
            
            requests_mock.post(
                'https://{}/oauth/token'.format(auth_configs.AUTH0_DOMAIN), 
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

            auth_configs = load_auth_config()

            with mock.patch.dict(os.environ, {"MINDGARD_API_KEY": "test token"}):
                requests_mock.post(
                    'https://{}/oauth/token'.format(auth_configs.AUTH0_DOMAIN), 
                    json={'access_token': 'test tokenasdf'}
                )
                assert 'test tokenasdf' == load_access_token()

# Test loads the config from instance file
def test_load_instance_config() -> None:
    config = generate_instance_config()
    cliconfig = instance_auth_config(config)
    assert cliconfig.AUTH0_DOMAIN == config['domain']
    assert cliconfig.AUTH0_CLIENT_ID == config['clientId']
    assert cliconfig.AUTH0_AUDIENCE == config['audience']
    assert cliconfig.DASHBOARD_URL == config['dashboardUrl']
    assert cliconfig.API_BASE == config["apiBase"]

# Test loading sandbox config
def test_load_sandbox_config() -> None:
    cliconfig = sandbox_auth_config()
    assert cliconfig.AUTH0_DOMAIN == "login.sandbox.mindgard.ai"
    assert cliconfig.AUTH0_CLIENT_ID == "U0OT7yZLJ4GEyabar11BENeQduu4MaNO"
    assert cliconfig.AUTH0_AUDIENCE == "https://marketplace-orchestrator.com"
    assert cliconfig.DASHBOARD_URL == "https://sandbox.mindgard.ai"
    assert cliconfig.API_BASE == "https://api.sandbox.mindgard.ai/api/v1"

# Test clear instance file
def test_instance_clearing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            token_file = get_instance_file()
            with open(token_file, 'w') as f:
                config = generate_instance_config()
                f.write(json.dumps(config))
            assert os.path.exists(token_file)
            clear_instance()
            assert not os.path.exists(token_file)

# Test clears the instance file on logout
def test_instance_logout() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"MINDGARD_CONFIG_DIR": tmpdir}):
            with mock.patch("mindgard.config.is_instance_set") as mock_is_instance_set:
                mock_is_instance_set.return_value = True
                token_file = get_instance_file()
                with open(token_file, 'w') as f:
                    f.write('test token')
                assert os.path.exists(token_file)
                logout()
                assert not os.path.exists(token_file)