from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.auth import (
    get_password_hash,
    send_telegram_login_notification,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.auth.auth_schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    ProfileUpdate,
    PasswordChange,
    EmailVerification,
    ResendVerification,
    MessageResponse,
)
from app.auth.email_service import (
    generate_verification_token,
    get_verification_token_expiry,
    send_verification_email,
)
from app.core.database import get_db
from app.auth.models import User

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send verification email."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Generate verification token
    verification_token = generate_verification_token()

    # Create new user
    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        email_verified=False,
        verification_token=verification_token,
        verification_token_expires=get_verification_token_expiry(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email (non-blocking, don't fail registration if email fails)
    send_verification_email(user.email, user.name, verification_token)

    return user


@auth_router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox.",
        )

    access_token = create_access_token(data={"sub": user.id})
    send_telegram_login_notification(user.email, name=user.name)
    return Token(access_token=access_token)


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user


@auth_router.post("/verify-email", response_model=MessageResponse)
def verify_email(data: EmailVerification, db: Session = Depends(get_db)):
    """Verify user's email with the verification token."""
    user = db.query(User).filter(User.verification_token == data.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    if user.email_verified:
        return MessageResponse(message="Email already verified")

    if (
        user.verification_token_expires
        and user.verification_token_expires < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one.",
        )

    # Mark email as verified
    user.email_verified = True
    # We keep the token so that if the user clicks the link again, we can tell them "Already verified"
    # instead of "Invalid token". The token will naturally expire or be replaced on next request.
    # user.verification_token = None
    # user.verification_token_expires = None
    db.commit()

    return MessageResponse(message="Email verified successfully")


@auth_router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(data: ResendVerification, db: Session = Depends(get_db)):
    """Resend verification email."""
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        # Don't reveal if email exists
        return MessageResponse(
            message="If the email exists, a verification link has been sent"
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified"
        )

    # Generate new token
    verification_token = generate_verification_token()
    user.verification_token = verification_token
    user.verification_token_expires = get_verification_token_expiry()
    db.commit()

    # Send email
    send_verification_email(user.email, user.name, verification_token)

    return MessageResponse(
        message="If the email exists, a verification link has been sent"
    )


# Profile CRUD endpoints
@auth_router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user


@auth_router.put("/profile", response_model=UserResponse)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile (name)."""
    current_user.name = data.name
    db.commit()
    db.refresh(current_user)
    return current_user


@auth_router.put("/profile/password", response_model=MessageResponse)
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully")
