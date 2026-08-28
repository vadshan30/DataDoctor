from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
import html
import logging
import secrets
import time
from urllib.parse import quote

import resend

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

_RESET_TOKEN_TTL_MINUTES = 30


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def send_reset_email(email: str, reset_link: str) -> None:
    """Send a password reset email through Resend."""
    if not settings.RESEND_API_KEY or not settings.FROM_EMAIL:
        raise RuntimeError("RESEND_API_KEY and FROM_EMAIL must be configured")
    if "@" not in settings.FROM_EMAIL:
        raise RuntimeError("FROM_EMAIL must be a valid email address")

    resend.api_key = settings.RESEND_API_KEY
    safe_email = html.escape(email)
    safe_reset_link = html.escape(reset_link, quote=True)

    resend.Emails.send(
        {
            "from": settings.FROM_EMAIL,
            "to": [email],
            "subject": "Reset your DataDoctor password",
            "html": f"""
                <div style="margin:0;background:#f4f7f6;padding:40px 16px;font-family:Arial,sans-serif;color:#1f2933">
                    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #d9e2df;border-radius:12px;padding:40px">
                        <p style="margin:0 0 24px;color:#0f766e;font-size:24px;font-weight:700">DataDoctor</p>
                        <h1 style="margin:0 0 16px;font-size:26px;color:#172b2a">Reset your password</h1>
                        <p style="font-size:16px;line-height:1.6">We received a request to reset the password for {safe_email}.</p>
                        <p style="font-size:16px;line-height:1.6">Use the button below to choose a new password. This link expires in 30 minutes.</p>
                        <p style="margin:32px 0"><a href="{safe_reset_link}" style="display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;border-radius:8px;padding:14px 24px;font-weight:700">Reset password</a></p>
                        <p style="font-size:13px;line-height:1.6;color:#52605e">If the button does not work, copy and paste this link into your browser:</p>
                        <p style="font-size:13px;line-height:1.6;word-break:break-all"><a href="{safe_reset_link}" style="color:#0f766e">{safe_reset_link}</a></p>
                        <p style="margin:28px 0 0;font-size:13px;line-height:1.6;color:#52605e">If you did not request a password reset, you can safely ignore this email. Your password will not change.</p>
                    </div>
                </div>
            """,
            "text": (
                "Reset your DataDoctor password\n\n"
                "Use this link to choose a new password (expires in 30 minutes):\n"
                f"{reset_link}\n\n"
                "If you did not request a password reset, you can safely ignore this email."
            ),
        }
    )


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
    
    Only sends email if the user exists in the database.
    Returns a clear error if the email is not registered.
    """
    now = datetime.now(timezone.utc)
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now))
    db.commit()

    # Check if user exists
    user = db.scalar(select(User).where(User.email == payload.email))
    
    # If user doesn't exist, return 404 error
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found",
        )

    # User exists - persist the token before sending the email.
    token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=now + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset_token)
    db.commit()
    reset_link = f"http://localhost:5173/reset-password?token={quote(token)}"
    
    try:
        send_reset_email(payload.email, reset_link)
        logger.info(f"Password reset email sent to {payload.email}")
    except Exception as e:
        logger.exception("Unable to send password reset email")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset email. Please try again later.",
        )
    
    return {"message": "Password reset link sent to your email"}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Consume a reset token and update the user's password."""
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    now = datetime.now(timezone.utc)
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now))
    db.commit()

    record = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token == payload.token)
    )
    if not record or record.used or record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.scalar(select(User).where(User.id == record.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for this email",
        )

    user.hashed_password = hash_password(payload.new_password)
    record.used = True
    db.commit()
    logger.info(f"Password reset successfully for {user.email}")
    return {"message": "Password updated successfully"}