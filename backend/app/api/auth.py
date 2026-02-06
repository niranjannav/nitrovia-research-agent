"""Authentication routes."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.models.schemas import (
    LoginRequest,
    SignupRequest,
    UserResponse,
    AuthResponse,
)
from app.services.supabase import get_supabase_client

router = APIRouter()


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Register a new user."""
    supabase = get_supabase_client()

    try:
        # Create user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name,
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
            "email": request.email,
            "full_name": request.full_name,
        }).execute()

        return AuthResponse(
            user=UserResponse(
                id=auth_response.user.id,
                email=auth_response.user.email,
                full_name=request.full_name,
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
async def login(request: LoginRequest):
    """Login with email and password."""
    supabase = get_supabase_client()

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
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
