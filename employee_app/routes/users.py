from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_roles
from models.user import User
from services.auth_service import hash_password


router = APIRouter(
    prefix="/users",
    tags=["User Management"]
)


# ============================================================
# Request models
# ============================================================

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str


class UpdatePasswordRequest(BaseModel):
    password: str


# ============================================================
# Get all users
# Admin only
# ============================================================

@router.get("/")
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    users = (
        db.query(User)
        .order_by(User.id.asc())
        .all()
    )

    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        for user in users
    ]


# ============================================================
# Create user
# Admin only
# ============================================================

@router.post("/")
def create_user(
    user_data: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    allowed_roles = {
        "admin",
        "hr",
        "employee"
    }

    role = user_data.role.lower().strip()

    if role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Use admin, hr, or employee."
        )

    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long."
        )

    existing_username = (
        db.query(User)
        .filter(User.username == user_data.username)
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already exists."
        )

    existing_email = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already exists."
        )

    new_user = User(
        username=user_data.username.strip(),
        email=user_data.email.strip(),
        password=hash_password(user_data.password),
        role=role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully.",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "is_active": new_user.is_active
        }
    }


# ============================================================
# Activate / deactivate user
# Admin only
# ============================================================

@router.put("/{user_id}/status")
def update_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    # Prevent admin from disabling their own account.
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own account status."
        )

    user.is_active = not user.is_active

    db.commit()
    db.refresh(user)

    return {
        "message": "User status updated successfully.",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
    }


# ============================================================
# Reset password
# Admin only
# ============================================================

@router.put("/{user_id}/password")
def reset_user_password(
    user_id: int,
    password_data: UpdatePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    if len(password_data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long."
        )

    user.password = hash_password(password_data.password)

    db.commit()

    return {
        "message": "Password reset successfully."
    }