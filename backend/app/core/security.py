from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Reduce bcrypt rounds in development for faster login (10ms vs 200ms)
# In production, use the default of 12 rounds for security
_is_dev = settings.APP_ENV.lower() in ("development", "dev", "local")
_bcrypt_rounds = 4 if _is_dev else 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=_bcrypt_rounds)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta is not None:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
