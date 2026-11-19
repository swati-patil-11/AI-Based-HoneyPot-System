from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security_database import SecuritySessionLocal
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token
)
from services.blocking_service import get_active_block
from services.request_utils import get_client_ip


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# =========================
# Request Models
# =========================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "employee"


class LoginRequest(BaseModel):
    username: str
    password: str


# =========================
# Register User
# Supports Employee, HR, and Admin self-registration
# =========================

@router.post("/register")
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    # Validate and normalize requested role
    role = (user_data.role or "employee").strip().lower()
    if role not in ("employee", "hr", "admin"):
        raise HTTPException(
            status_code=400,
            detail="Role must be one of: employee, hr, admin"
        )

    # Check duplicate username
    existing_user = (
        db.query(User)
        .filter(User.username == user_data.username)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"Username '{user_data.username}' is already taken"
        )

    # Check duplicate email
    existing_email = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail=f"Email '{user_data.email}' is already registered"
        )

    # Hash password
    hashed_password = hash_password(
        user_data.password
    )

    # Create new user with chosen role
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password,
        role=role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Link profile so dashboard works immediately for employee and HR roles
    try:
        from datetime import date
        from models.employee import Employee
        from models.department import Department
        from models.salary import Salary

        first_dept = db.query(Department).first()
        dept_id = first_dept.id if first_dept else 1

        emp_count = db.query(Employee).count()
        emp_code = f"EMP{2000 + emp_count + 1}"

        designation_map = {
            "admin": "Security Administrator",
            "hr": "HR Manager",
            "employee": "Software Associate"
        }
        designation = designation_map.get(role, "Software Associate")

        new_emp = Employee(
            employee_id=emp_code,
            first_name=user_data.username.capitalize(),
            last_name="Staff",
            email=user_data.email,
            phone="9876543210",
            department_id=dept_id,
            designation=designation,
            joining_date=date.today(),
            employment_status="Active",
            user_id=new_user.id
        )
        db.add(new_emp)
        db.flush()

        base_salary_map = {
            "admin": 90000,
            "hr": 65000,
            "employee": 45000
        }
        new_salary = Salary(
            employee_id=new_emp.id,
            basic_salary=base_salary_map.get(role, 45000),
            allowances=5000,
            deductions=2000,
            currency="INR"
        )
        db.add(new_salary)
        db.commit()
    except Exception as e:
        db.rollback()
        pass

    role_label = {"admin": "Administrator", "hr": "HR Manager", "employee": "Employee"}.get(role, "User")

    return {
        "message": f"{role_label} account registered successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role
        }
    }



# =========================
# Login
# =========================

@router.post("/login")
def login(
    user_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    # Requirement 3: If IP is blocked, login MUST be refused immediately!
    client_ip = get_client_ip(request)
    sec_db = SecuritySessionLocal()
    try:
        active_block = get_active_block(sec_db, client_ip)
        if active_block:
            raise HTTPException(
                status_code=403,
                detail=f"Your IP address is temporarily blocked. Access to login is denied until {active_block.expires_at.isoformat()}Z."
            )
    finally:
        sec_db.close()

    # Find user
    user = (
        db.query(User)
        .filter(User.username == user_data.username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Check account status
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # Verify password
    if not verify_password(
        user_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }