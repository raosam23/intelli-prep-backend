import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional

class RegisterRequest(BaseModel):
    name: str = Field(description="User's full name")
    email: EmailStr = Field(description="User's email address")
    password: str = Field(description="User's password", min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr = Field(description="User's email address")
    password: str = Field(description="User's password")

class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT Access Token")
    token_type: str = Field(description="Type of the token, typically 'bearer'", default="bearer")

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(description="Unique identifier for the user")
    name: str = Field(description="User's full name")
    email: EmailStr = Field(description="User's email address")
    created_at: datetime = Field(description="Timestamp when the user was created")

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(description="User's full name", default=None)
    password: Optional[str] = Field(description="User's new password", min_length=8, default=None)

class UpdateProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(description="Unique identifier for the user")
    name: str = Field(description="User's full name")
    email: EmailStr = Field(description="User's email address")
    updated_at: datetime = Field(description="Timestamp when the user was last updated")