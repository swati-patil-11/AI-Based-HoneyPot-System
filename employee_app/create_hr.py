from database import SessionLocal
from models.user import User
from services.auth_service import hash_password


HR_USERNAME = "hr"
HR_EMAIL = "hr@example.com"
HR_PASSWORD = "HR@123"


def create_or_reset_hr():
    db = SessionLocal()

    try:
        hr = (
            db.query(User)
            .filter(User.username == HR_USERNAME)
            .first()
        )

        if hr:
            hr.email = HR_EMAIL
            hr.password = hash_password(HR_PASSWORD)
            hr.role = "hr"
            hr.is_active = True

            db.commit()

            print("HR account already existed.")
            print("HR account has been reset successfully.")

        else:
            hr = User(
                username=HR_USERNAME,
                email=HR_EMAIL,
                password=hash_password(HR_PASSWORD),
                role="hr",
                is_active=True
            )

            db.add(hr)
            db.commit()
            db.refresh(hr)

            print("HR account created successfully.")

        print()
        print("Username:", HR_USERNAME)
        print("Password:", HR_PASSWORD)
        print("Role:", hr.role)
        print("User ID:", hr.id)

    finally:
        db.close()


if __name__ == "__main__":
    create_or_reset_hr()