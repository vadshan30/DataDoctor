from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import secrets
import time

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

router = APIRouter()


@router.post("/register")
def register(email: str, password: str, full_name: str | None = None, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
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
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
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
def guest_login(db: Session = Depends(get_db)):
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
