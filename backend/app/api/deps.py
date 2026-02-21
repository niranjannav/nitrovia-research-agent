"""Dependency injection for API routes."""

import logging
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)
security = HTTPBearer()


@dataclass
class AuthenticatedUser:
    """Enriched user object with role and quota information."""

    id: str
    email: str
    full_name: str | None = None
    role: str = "user"
    monthly_report_limit: int = 3
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthenticatedUser:
    """
    Verify Supabase JWT and return the current user with role/quota info.

    Raises HTTPException if token is invalid or user is deactivated.
    """
    token = credentials.credentials
    supabase = get_supabase_client()

    try:
        # Verify the JWT with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        supabase_user = user_response.user

        # Fetch user profile with role and quota from users table
        user_data = supabase.table("users").select(
            "full_name, role, monthly_report_limit, is_active"
        ).eq("id", supabase_user.id).single().execute()

        profile = user_data.data or {}

        # Check if user is deactivated
        if profile.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact support.",
            )

        return AuthenticatedUser(
            id=supabase_user.id,
            email=supabase_user.email,
            full_name=profile.get("full_name"),
            role=profile.get("role", "user"),
            monthly_report_limit=profile.get("monthly_report_limit", 3),
            is_active=profile.get("is_active", True),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Type alias for dependency injection
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
