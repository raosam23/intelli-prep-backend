from bcrypt import hashpw, gensalt, checkpw
from app.core.config import settings
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from datetime import  timedelta, datetime, timezone

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return hashpw(password.encode("utf-8"), gensalt(settings.SALT_ROUNDS)).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hashed password."""
    return checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: Dict[str, Any]) -> str:
    """Create a JWT Access Token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT Access Token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None