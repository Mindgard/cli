
from typing import Any

# Note that these definitions ignore the existence _private methods

class AsymmetricSignatureVerifier:
    def __init__(
        self,
        jwks_url: str,
        algorithm: str = "RS256",
        cache_ttl: int = 600, # In their codebase this links to a classvar constant instead
    ) -> None: ...
    def verify_signature(self, token: str) -> dict[str, Any]: ...

class TokenVerifier:
    def __init__(self, signature_verifier: AsymmetricSignatureVerifier, issuer: str, audience: str) -> None: ...
    def verify(
        self,
        token: str,
        nonce: str | None = None,
        max_age: int | None = None,
        organization: str | None = None,
    ) -> dict[str, Any]: ...