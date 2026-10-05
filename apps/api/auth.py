import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Header, HTTPException
from packages.db.session import SessionLocal
from sqlalchemy import text

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
        self.require_issuer_audience = os.getenv("AUTH_REQUIRE_ISSUER_AUDIENCE", "true").lower() in {"1", "true", "yes"}
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
        keys = payload.get("keys", [])
        self._keys = {key["kid"]: key for key in keys if key.get("kid")}
        self._expires_at = time.monotonic() + 300
        return self._keys

    async def verify(self, token: str) -> dict[str, Any]:
        if self.require_issuer_audience and (not self.issuer or not self.audience):
            raise HTTPException(status_code=503, detail="oidc_issuer_audience_not_configured")
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
            key = (jwt.algorithms.ECAlgorithm.from_jwk(key_data)
                   if algorithm.startswith("ES") else jwt.algorithms.RSAAlgorithm.from_jwk(key_data))
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
    subject = str(payload["sub"])
    tenant = str(tenant_id)
    token_roles = frozenset(str(role) for role in roles)
    if os.getenv("AUTH_REQUIRE_MEMBERSHIP", "true").lower() in {"1", "true", "yes"}:
        async with SessionLocal() as session:
            row = (await session.execute(text(
                "SELECT roles FROM tenant_memberships WHERE tenant_id = :tenant AND subject = :subject AND active = TRUE"
            ), {"tenant": tenant, "subject": subject})).first()
        if row is None:
            raise HTTPException(status_code=403, detail="tenant_membership_required")
        db_roles = row[0] if isinstance(row[0], list) else []
        return RequestPrincipal(subject=subject, tenant_id=tenant, roles=frozenset(str(role) for role in db_roles))
    return RequestPrincipal(subject=subject, tenant_id=tenant, roles=token_roles)

async def require_principal(
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> RequestPrincipal:
    mode = os.getenv("AUTH_MODE", "oidc").lower()
    if mode != "oidc":
        if mode != "development":
            raise HTTPException(status_code=503, detail="unsupported_auth_mode")
        if os.getenv("ENVIRONMENT", "production").lower() == "production":
            raise HTTPException(status_code=503, detail="development_auth_disabled")
        if not x_tenant_id or not x_actor:
            raise HTTPException(status_code=401, detail="authentication_required")
        return RequestPrincipal(x_actor, x_tenant_id, frozenset({"developer", "approver", "admin"}))
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="bearer_token_required")
    return await principal_from_token(authorization[7:].strip())
