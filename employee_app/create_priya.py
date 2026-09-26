from database import SessionLocal
from models.user import User
from services.auth_service import hash_password


PRIYA_USERNAME = "priya"
PRIYA_EMAIL = "priya@example.com"
PRIYA_PASSWORD = "Priya@123"


def create_or_reset_priya():
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.username == PRIYA_USERNAME)
            .first()
        )

        if user:
            user.email = PRIYA_EMAIL
            user.password = hash_password(PRIYA_PASSWORD)
            user.role = "employee"
            user.is_active = True

            db.commit()

            print("Priya account already existed.")
            print("Priya account has been reset successfully.")

        else:
            user = User(
                username=PRIYA_USERNAME,
                email=PRIYA_EMAIL,
                password=hash_password(PRIYA_PASSWORD),
                role="employee",
                is_active=True
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            print("Priya account created successfully.")

        print()
        print("Username:", PRIYA_USERNAME)
        print("Password:", PRIYA_PASSWORD)
        print("Role:", user.role)
        print("User ID:", user.id)

    finally:
        db.close()


if __name__ == "__main__":
    create_or_reset_priya()