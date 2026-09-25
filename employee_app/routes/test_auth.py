from fastapi import APIRouter, Depends

from dependencies import get_current_user
from models.user import User


router = APIRouter(
    prefix="/test",
    tags=["Authentication Test"]
)


@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):

    return {
        "message": "You are authenticated",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role
        }
    }