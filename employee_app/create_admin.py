from database import SessionLocal
from models.user import User
from services.auth_service import hash_password


ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123"


def create_or_reset_admin():
    db = SessionLocal()

    try:
        admin = (
            db.query(User)
            .filter(User.username == ADMIN_USERNAME)
            .first()
        )

        if admin:
            # Reset existing admin account
            admin.email = ADMIN_EMAIL
            admin.password = hash_password(ADMIN_PASSWORD)
            admin.role = "admin"
            admin.is_active = True

            db.commit()

            print("Admin account already existed.")
            print("Admin account has been reset successfully.")

        else:
            # Create new admin account
            admin = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                password=hash_password(ADMIN_PASSWORD),
                role="admin",
                is_active=True
            )

            db.add(admin)
            db.commit()
            db.refresh(admin)

            print("Admin account created successfully.")

        print()
        print("Username:", ADMIN_USERNAME)
        print("Password:", ADMIN_PASSWORD)
        print("Role: admin")

    finally:
        db.close()


if __name__ == "__main__":
    create_or_reset_admin()