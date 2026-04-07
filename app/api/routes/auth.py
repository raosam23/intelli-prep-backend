from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.services.auth_service import register_user, login_user, update_user_profile
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse, TokenResponse, UpdateProfileRequest, UpdateProfileResponse
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session)) -> UserResponse:
    """Endpoint to register a new user."""
    return await register_user(session, request)

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """Endpoint to authenticate a user and return a JWT token."""
    return await login_user(session, request)

@router.put('/profile', response_model=UpdateProfileResponse)
async def update_profile(request: UpdateProfileRequest, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)) -> UpdateProfileResponse:
    """Endpoint to update the current user's profile information."""
    return await update_user_profile(session, current_user.id, request)

@router.get('/me', response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Endpoint to retrieve the current user's profile information."""
    return UserResponse.model_validate(current_user)