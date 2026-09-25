from fastapi import APIRouter, Depends

from dependencies import require_roles
from models.user import User


router = APIRouter(
    prefix="/role-test",
    tags=["Role Testing"]
)


@router.get("/admin")
def admin_only(
    current_user: User = Depends(
        require_roles("admin")
    )
):
    return {
        "message": "You have admin access",
        "username": current_user.username,
        "role": current_user.role
    }


@router.get("/hr")
def hr_only(
    current_user: User = Depends(
        require_roles("admin", "hr")
    )
):
    return {
        "message": "You have HR access",
        "username": current_user.username,
        "role": current_user.role
    }


@router.get("/employee")
def employee_access(
    current_user: User = Depends(
        require_roles("admin", "hr", "employee")
    )
):
    return {
        "message": "You have employee-level access",
        "username": current_user.username,
        "role": current_user.role
    }