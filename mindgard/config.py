import os
import json
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CliConfig:
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_AUDIENCE: str
    API_BASE: str
    DASHBOARD_URL: str

def get_config_directory() -> str:
    config_dir = os.environ.get('MINDGARD_CONFIG_DIR')
    return config_dir or os.path.join(os.path.expanduser('~'), '.mindgard')

def create_config_directory() -> None:
    os.makedirs(get_config_directory(), exist_ok=True)
    
def get_token_file() -> str:
    return os.path.join(get_config_directory(), 'token.txt')

def get_instance_file() -> str:
    return os.path.join(get_config_directory(), 'instance.txt')

def is_instance_set() -> bool:
    return os.path.isfile(os.path.join(get_config_directory(), 'instance.txt'))

def instance_auth_config(config: Dict[str, Any]) -> CliConfig:
    return CliConfig(
        AUTH0_DOMAIN=os.getenv("AUTH0_DOMAIN", str(config['domain'])),
        AUTH0_CLIENT_ID=os.getenv("AUTH0_CLIENT_ID", str(config['clientId'])),
        AUTH0_AUDIENCE=os.getenv("AUTH0_AUDIENCE", str(config['audience'])),
        API_BASE=os.getenv("API_BASE", str(config['apiBase'])),
        DASHBOARD_URL=os.getenv("DASHBOARD_URL", str(config['dashboardUrl']))
    )

def sandbox_auth_config() -> CliConfig:
    return CliConfig(
        AUTH0_DOMAIN=os.getenv("AUTH0_DOMAIN", "login.sandbox.mindgard.ai"),
        AUTH0_CLIENT_ID=os.getenv("AUTH0_CLIENT_ID", "U0OT7yZLJ4GEyabar11BENeQduu4MaNO"),
        AUTH0_AUDIENCE=os.getenv("AUTH0_AUDIENCE", "https://marketplace-orchestrator.com"),
        API_BASE=os.getenv("API_BASE", "https://api.sandbox.mindgard.ai/api/v1"),
        DASHBOARD_URL=os.getenv("DASHBOARD_URL", "https://sandbox.mindgard.ai")
    )

def load_auth_config() -> CliConfig:
    if is_instance_set():
        try:
            # If an instance config exists then load the variables
            with open(get_instance_file(), 'r') as f:
                instance_config = json.load(f)
            
            return instance_auth_config(instance_config)
        except:
            # jsonDecodeError & KeyError
            # TODO: Handle this automatically
            raise KeyError("Unable to load instance configuration. To create a new configuration run `mindgard logout` and then `mindgard login --instance XXXX`")
    else:
        # Default sandbox constants
        return sandbox_auth_config()
