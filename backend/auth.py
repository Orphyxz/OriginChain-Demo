import logging
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from .domain import UserRole


LOGGER = logging.getLogger("originchain.auth")
ALGORITHM = "HS256"
ISSUER = "originchain-local-demo"
DEVELOPMENT_SECRET = "originchain-local-demo-only-change-this-secret-before-sharing"
PASSWORD_HASH = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False, scheme_name="OriginChainBearer")


DEMO_ACCOUNTS = (
    {
        "id": "user_admin",
        "username": "admin",
        "display_name": "OriginChain Demo Admin",
        "role": UserRole.ADMIN.value,
        "organization_name": "OriginChain",
        "password": "OriginDemo2026!",
    },
    {
        "id": "user_supplier",
        "username": "supplier",
        "display_name": "Lumina Supplier Operator",
        "role": UserRole.RAW_MATERIAL_SUPPLIER.value,
        "organization_name": "Lumina Actives",
        "password": "OriginDemo2026!",
    },
    {
        "id": "user_manufacturer",
        "username": "manufacturer",
        "display_name": "Aurelia Manufacturing Operator",
        "role": UserRole.MANUFACTURER.value,
        "organization_name": "Aurelia Manufacturing Atelier",
        "password": "OriginDemo2026!",
    },
    {
        "id": "user_distributor",
        "username": "distributor",
        "display_name": "Prestige Distribution Operator",
        "role": UserRole.DISTRIBUTOR.value,
        "organization_name": "Prestige Beauty Distribution",
        "password": "OriginDemo2026!",
    },
    {
        "id": "user_retailer",
        "username": "retailer",
        "display_name": "Maison Luxe Retail Operator",
        "role": UserRole.RETAILER.value,
        "organization_name": "Maison Luxe Retail",
        "password": "OriginDemo2026!",
    },
)


@lru_cache(maxsize=16)
def hash_password(password: str, account_id: str) -> str:
    """Cache seed work per actor while retaining a distinct Argon2 salt per account."""
    return PASSWORD_HASH.hash(password)


def safe_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "organization_name": user["organization_name"],
        "active": bool(user["active"]),
    }


class AuthService:
    def __init__(self, secret: str | None = None, access_token_minutes: int | None = None):
        configured_secret = secret or os.environ.get("ORIGINCHAIN_JWT_SECRET")
        self.using_development_secret = not bool(configured_secret)
        self.secret = configured_secret or DEVELOPMENT_SECRET
        if self.using_development_secret:
            LOGGER.warning(
                "ORIGINCHAIN_JWT_SECRET is not set; using an unsafe local-demo fallback."
            )
        configured_minutes = access_token_minutes
        if configured_minutes is None:
            try:
                configured_minutes = int(os.environ.get("ORIGINCHAIN_ACCESS_TOKEN_MINUTES", "30"))
            except ValueError:
                configured_minutes = 30
                LOGGER.warning("Invalid ORIGINCHAIN_ACCESS_TOKEN_MINUTES; using 30 minutes.")
        self.access_token_minutes = max(1, min(configured_minutes, 24 * 60))

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return PASSWORD_HASH.verify(password, password_hash)
        except Exception:
            return False

    def create_access_token(
        self,
        user: dict[str, Any],
        *,
        now: datetime | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + (expires_delta or timedelta(minutes=self.access_token_minutes))
        return jwt.encode(
            {
                "sub": user["id"],
                "role": user["role"],
                "iat": issued_at,
                "exp": expires_at,
                "iss": ISSUER,
            },
            self.secret,
            algorithm=ALGORITHM,
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(
            token,
            self.secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["sub", "role", "iat", "exp", "iss"]},
        )


def seed_demo_users(repository: Any) -> None:
    for account in DEMO_ACCOUNTS:
        repository.seed_user(
            {
                **{key: value for key, value in account.items() if key != "password"},
                "password_hash": hash_password(account["password"], account["id"]),
                "active": 1,
            }
        )


def authentication_error(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise authentication_error()
    try:
        claims = request.app.state.auth.decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise authentication_error("Session expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise authentication_error("Invalid authentication token.") from exc
    user = request.app.state.repository.get_user(claims.get("sub", ""))
    if not user or not user["active"] or user["role"] != claims.get("role"):
        raise authentication_error("User account is inactive or unavailable.")
    return user


def require_roles(*roles: UserRole) -> Callable[..., dict[str, Any]]:
    allowed = {role.value for role in roles}

    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role"] not in allowed:
            names = ", ".join(role.replace("_", " ").title() for role in sorted(allowed))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "You do not have permission to perform this action.",
                    "required_roles": sorted(allowed),
                    "guidance": f"This action is restricted to: {names}.",
                },
            )
        return user

    return dependency


authenticated_user = require_roles(*tuple(UserRole))
