from mindgard.config import load_auth_config
 
VERSION: str = "0.67.0"
REPOSITORY_URL: str = f"https://pypi.org/pypi/mindgard/json"

ALGORITHMS = ['RS256']

auth_config = load_auth_config()
AUTH0_DOMAIN = auth_config.AUTH0_DOMAIN
AUTH0_CLIENT_ID = auth_config.AUTH0_CLIENT_ID
AUTH0_AUDIENCE = auth_config.AUTH0_AUDIENCE
API_BASE = auth_config.API_BASE
DASHBOARD_URL = auth_config.DASHBOARD_URL

API_RETRY_ATTEMPTS = 10
API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS = 3
DEFAULT_RISK_THRESHOLD = 50

EXIT_CODE_PASSED = 0
EXIT_CODE_NOT_PASSED = 1
EXIT_CODE_ERROR = 2

ATTACK_STATE_QUEUED = 0
ATTACK_STATE_RUNNING = 1
ATTACK_STATE_COMPLETED = 2
ATTACK_STATE_ERRORED = -1