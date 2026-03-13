import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.security import hash_password, verify_password, create_access_token
from sqlmodel import select
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, RegisterRequest, UpdateProfileRequest, UpdateProfileResponse

async def register_user(session: AsyncSession, data: RegisterRequest) -> UserResponse:
    """Registers a new user in the system."""
    user_res = await session.execute(select(User).where(User.email == data.email))
    user = user_res.scalars().first()
    if user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = hash_password(data.password)
    new_user = User(email=data.email, name=data.name, hashed_password=hashed_password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return UserResponse.model_validate(new_user)

async def login_user(session: AsyncSession, data: LoginRequest) -> TokenResponse:
    """Authenticates a user and returns a JWT access token."""
    user_res = await session.execute(select(User).where(User.email == data.email))
    user = user_res.scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, token_type="bearer")
    
async def update_user_profile(session: AsyncSession, user_id: uuid.UUID, data: UpdateProfileRequest) -> UpdateProfileResponse:
    """Update the user's profile information."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if data.name is not None:
        user.name = data.name
    if data.password is not None:
        if verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as the old password")
        user.hashed_password = hash_password(data.password)
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UpdateProfileResponse.model_validate(user)