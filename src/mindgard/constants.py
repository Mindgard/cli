import os

VERSION: str = "0.38.0"
REPOSITORY_URL: str = f"https://pypi.org/pypi/mindgard/json"

ALGORITHMS = ['RS256']
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "login.sandbox.mindgard.ai")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "U0OT7yZLJ4GEyabar11BENeQduu4MaNO")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://marketplace-orchestrator.com")

API_BASE = os.getenv("API_BASE", "https://api.sandbox.mindgard.ai/api/v1")

API_RETRY_ATTEMPTS = 10
API_RETRY_WAIT_BETWEEN_ATTEMPTS_SECONDS = 3