from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
import secrets
import time

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

router = APIRouter()

# In-memory store for password reset tokens.
# Format: { token: { email: str, expires_at: float } }
# For a real deployment, persist this in the database with an expiry.
_PASSWORD_RESET_TOKENS: dict[str, dict] = {}
_RESET_TOKEN_TTL_SECONDS = 60 * 30  # 30 minutes


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register")
async def register(email: str, password: str, full_name: str | None = None, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}


@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    # db.scalar() is slightly faster than .query().first() for a single-row lookup
    # and reuses the existing email index on the users table.
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }


@router.post("/guest")
async def guest_login(db: Session = Depends(get_db)):
    """Create a temporary guest user account"""
    # Generate a unique email for the guest
    timestamp = int(time.time())
    random_str = secrets.token_hex(8)
    guest_email = f"guest-{timestamp}-{random_str}@datadoctor.local"

    # Generate a random password
    guest_password = secrets.token_hex(16)

    # Create guest user with full_name indicating it's a guest
    user = User(
        email=guest_email,
        hashed_password=hash_password(guest_password),
        full_name="Guest User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Return auth response
    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generate a password reset token for the given email.

    Returns success even when the email is not found to avoid leaking which
    addresses are registered. The token is logged to stdout so the developer
    can use it without an email service in development.
    """
    # Garbage-collect expired tokens to bound memory usage
    now = time.time()
    for tok in [t for t, rec in _PASSWORD_RESET_TOKENS.items() if rec["expires_at"] < now]:
        _PASSWORD_RESET_TOKENS.pop(tok, None)

    user = db.scalar(select(User).where(User.email == payload.email))
    if user:
        token = secrets.token_urlsafe(32)
        _PASSWORD_RESET_TOKENS[token] = {
            "email": payload.email,
            "expires_at": now + _RESET_TOKEN_TTL_SECONDS,
        }
        reset_link = f"http://localhost:5173/reset-password?token={token}"
        print(f"[DataDoctor] Password reset link for {payload.email}: {reset_link}")
    return {"message": "Password reset link sent to your email"}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Consume a reset token and update the user's password."""
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    record = _PASSWORD_RESET_TOKENS.pop(payload.token, None)
    if not record or record["expires_at"] < time.time():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.scalar(select(User).where(User.email == record["email"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for this email",
        )

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
