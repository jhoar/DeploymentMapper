from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

_ROLE_ORDER = {"reader": 1, "editor": 2, "admin": 3}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthContext:
    role: str
    subject: str
    auth_type: str



def auth_mode() -> str:
    return os.getenv("DEPLOYMENT_MAPPER_AUTH_MODE", "none").strip().lower()


def _normalize_role(role: str | None) -> str | None:
    if not role:
        return None
    candidate = role.strip().lower()
    return candidate if candidate in _ROLE_ORDER else None


def _api_key_role_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for role in _ROLE_ORDER:
        raw = os.getenv(f"DEPLOYMENT_MAPPER_API_KEYS_{role.upper()}", "")
        for key in [value.strip() for value in raw.split(",") if value.strip()]:
            mapping[key] = role
    return mapping


def _extract_role_from_claims(claims: dict[str, Any]) -> str | None:
    role = _normalize_role(str(claims.get("role"))) if claims.get("role") is not None else None
    if role:
        return role

    roles = claims.get("roles")
    if isinstance(roles, list):
        for candidate in roles:
            normalized = _normalize_role(str(candidate))
            if normalized:
                return normalized
    return None


def _decode_jwt(token: str) -> dict[str, Any]:
    try:
        import jwt
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyJWT is required for JWT auth mode.",
        ) from exc

    secret = os.getenv("DEPLOYMENT_MAPPER_JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEPLOYMENT_MAPPER_JWT_SECRET must be configured for JWT auth mode.",
        )

    algorithm = os.getenv("DEPLOYMENT_MAPPER_JWT_ALGORITHM", "HS256")
    audience = os.getenv("DEPLOYMENT_MAPPER_JWT_AUDIENCE")

    try:
        options = {"verify_aud": bool(audience)}
        claims = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            audience=audience if audience else None,
            options=options,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not isinstance(claims, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def get_auth_context(
    api_key: str | None = Depends(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> AuthContext:
    mode = auth_mode()
    if mode in {"", "none", "off", "disabled"}:
        return AuthContext(role="admin", subject="anonymous", auth_type="none")

    allowed_modes = {"api_key", "jwt", "api_key_or_jwt"}
    if mode not in allowed_modes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported auth mode: {mode}",
        )

    if mode in {"api_key", "api_key_or_jwt"} and api_key:
        role = _api_key_role_map().get(api_key)
        if role:
            return AuthContext(role=role, subject="api-key", auth_type="api_key")

    if mode in {"jwt", "api_key_or_jwt"} and bearer and bearer.credentials:
        claims = _decode_jwt(bearer.credentials)
        role = _extract_role_from_claims(claims)
        if role:
            subject = str(claims.get("sub") or claims.get("client_id") or "jwt-subject")
            return AuthContext(role=role, subject=subject, auth_type="jwt")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(minimum_role: str) -> Callable[[AuthContext], AuthContext]:
    normalized_minimum = _normalize_role(minimum_role)
    if normalized_minimum is None:
        raise ValueError(f"Unknown role: {minimum_role}")

    def _dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if _ROLE_ORDER[context.role] < _ROLE_ORDER[normalized_minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{normalized_minimum} role required.",
            )
        return context

    return _dependency
