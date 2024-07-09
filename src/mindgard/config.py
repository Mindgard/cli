import os
from typing import Optional

def load_instance_api_base() -> Optional[str]:
    # Check our local config for instance being set?
    # grab the instance vars and set the local env (set env on every run)
    #API_BASE = get_from_local_config()
    #api_url = "https://api.{}.mindgard.ai/api/v1".format("test")
    api_url = "https://api.sandbox.mindgard.ai/api/v1"
    
    return os.getenv("API_BASE", api_url)

def get_config_directory() -> str:
    config_dir = os.environ.get('MINDGARD_CONFIG_DIR')
    return config_dir or os.path.join(os.path.expanduser('~'), '.mindgard')

def create_config_directory() -> str:
    os.makedirs(get_config_directory(), exist_ok=True)
    
def get_token_file() -> str:
    return os.path.join(get_config_directory(), 'token.txt')

def get_instance_file() -> str:
    return os.path.join(get_config_directory(), 'instance.txt')