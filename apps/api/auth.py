import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Header, HTTPException

@dataclass(frozen=True)
class RequestPrincipal:
    subject: str
    tenant_id: str
    roles: frozenset[str]

class OIDCVerifier:
    def __init__(self) -> None:
        self.jwks_url = os.getenv("OIDC_JWKS_URL", "")
        self.issuer = os.getenv("OIDC_ISSUER", "")
        self.audience = os.getenv("OIDC_AUDIENCE", "")
        self._keys: dict[str, Any] = {}
        self._expires_at = 0.0

    async def _jwks(self) -> dict[str, Any]:
        if self._keys and time.monotonic() < self._expires_at:
            return self._keys
        if not self.jwks_url:
            raise HTTPException(status_code=503, detail="oidc_jwks_not_configured")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="oidc_jwks_unavailable") from exc
        payload = response.json()
        self._keys = {key["kid"]: key for key in payload.get("keys", []) if key.get("kid")}
        self._expires_at = time.monotonic() + 300
        return self._keys

    async def verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            algorithm = header.get("alg")
            if not kid or algorithm not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}:
                raise ValueError("invalid_token_header")
            key_data = (await self._jwks()).get(kid)
            if key_data is None:
                self._expires_at = 0
                key_data = (await self._jwks()).get(kid)
            if key_data is None:
                raise ValueError("unknown_signing_key")
            key = jwt.algorithms.ECAlgorithm.from_jwk(key_data) if algorithm.startswith("ES") else jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            options = {"require": ["exp", "iat", "sub"]}
            kwargs: dict[str, Any] = {"algorithms": [algorithm], "options": options}
            if self.issuer:
                kwargs["issuer"] = self.issuer
            if self.audience:
                kwargs["audience"] = self.audience
            return jwt.decode(token, key=key, **kwargs)
        except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=401, detail="invalid_access_token") from exc

verifier = OIDCVerifier()

def _claim(payload: dict[str, Any], name: str, default: Any = None) -> Any:
    value: Any = payload
    for part in name.split("."):
        if not isinstance(value, dict):
            return default
        value = value.get(part)
    return value if value is not None else default

async def principal_from_token(token: str) -> RequestPrincipal:
    payload = await verifier.verify(token)
    tenant_claim = os.getenv("OIDC_TENANT_CLAIM", "tenant_id")
    roles_claim = os.getenv("OIDC_ROLES_CLAIM", "roles")
    tenant_id = _claim(payload, tenant_claim)
    roles = _claim(payload, roles_claim, [])
    if not tenant_id or not isinstance(roles, (list, tuple, set)):
        raise HTTPException(status_code=403, detail="tenant_or_roles_claim_missing")
    return RequestPrincipal(
        subject=str(payload["sub"]),
        tenant_id=str(tenant_id),
        roles=frozenset(str(role) for role in roles),
    )

async def require_principal(
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> RequestPrincipal:
    mode = os.getenv("AUTH_MODE", "development").lower()
    if mode == "development":
        if not x_tenant_id or not x_actor:
            raise HTTPException(status_code=401, detail="authentication_required")
        return RequestPrincipal(x_actor, x_tenant_id, frozenset({"developer", "approver", "admin"}))
    if mode != "oidc":
        raise HTTPException(status_code=503, detail="unsupported_auth_mode")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="bearer_token_required")
    return await principal_from_token(authorization[7:].strip())
