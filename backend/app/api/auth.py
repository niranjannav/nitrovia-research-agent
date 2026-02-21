"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import CurrentUser
from app.models.schemas import (
    LoginRequest,
    SignupRequest,
    UserResponse,
    AuthResponse,
)
from app.services.quota import get_quota_status
from app.services.supabase import get_supabase_client

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/signup", response_model=AuthResponse)
@limiter.limit("5/minute")
async def signup(request: Request, body: SignupRequest):
    """Register a new user."""
    supabase = get_supabase_client()

    try:
        # Create user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": body.email,
            "password": body.password,
            "options": {
                "data": {
                    "full_name": body.full_name,
                }
            }
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user",
            )

        # Insert user record in users table
        supabase.table("users").insert({
            "id": auth_response.user.id,
            "email": body.email,
            "full_name": body.full_name,
        }).execute()

        return AuthResponse(
            user=UserResponse(
                id=auth_response.user.id,
                email=auth_response.user.email,
                full_name=body.full_name,
            ),
            access_token=auth_response.session.access_token if auth_response.session else None,
            refresh_token=auth_response.session.refresh_token if auth_response.session else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """Login with email and password."""
    supabase = get_supabase_client()

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Get user details from users table
        user_data = supabase.table("users").select("*").eq(
            "id", auth_response.user.id
        ).single().execute()

        return AuthResponse(
            user=UserResponse(
                id=auth_response.user.id,
                email=auth_response.user.email,
                full_name=user_data.data.get("full_name") if user_data.data else None,
            ),
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}",
        )


@router.post("/logout")
async def logout(current_user: CurrentUser):
    """Logout the current user."""
    supabase = get_supabase_client()

    try:
        supabase.auth.sign_out()
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information."""
    supabase = get_supabase_client()

    # Get user details from users table
    user_data = supabase.table("users").select("*").eq(
        "id", current_user.id
    ).single().execute()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=user_data.data.get("full_name") if user_data.data else None,
    )


@router.get("/quota")
async def get_user_quota(current_user: CurrentUser):
    """Get current user's quota status."""
    quota = get_quota_status(
        current_user.id, current_user.monthly_report_limit, current_user.is_admin,
    )
    return {
        "used": quota.used,
        "limit": quota.limit,
        "remaining": quota.remaining,
        "is_admin": quota.is_admin,
        "exceeded": quota.exceeded,
        "resets_at": quota.resets_at,
    }
