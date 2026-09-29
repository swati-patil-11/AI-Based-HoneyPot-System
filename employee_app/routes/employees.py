import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.employee import Employee
from models.department import Department
from models.user import User
from dependencies import require_roles


router = APIRouter(
    prefix="/employees",
    tags=["Employees"]
)


# ============================================================
# VALIDATION PATTERNS
# ============================================================

NAME_PATTERN = re.compile(r"^[A-Za-z]+$")
PHONE_PATTERN = re.compile(r"^\d{10}$")


def validate_name(value: str, field_name: str) -> str:
    """
    Validate fields that must contain letters only.
    Examples:
    John      -> valid
    Priya     -> valid
    John123   -> invalid
    John@     -> invalid
    John Doe  -> invalid
    """

    value = value.strip()

    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required"
        )

    if not NAME_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must contain characters only"
        )

    return value


def validate_phone(value: str | None) -> str | None:
    """
    Validate phone number.
    Phone is optional, but if provided it must contain
    exactly 10 digits.
    """

    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    if not PHONE_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail="Phone number must contain exactly 10 digits"
        )

    return value


# ============================================================
# REQUEST MODELS
# ============================================================

class EmployeeCreate(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    department_id: int
    designation: str
    joining_date: date
    employment_status: str = "Active"


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    department_id: int | None = None
    designation: str | None = None
    joining_date: date | None = None
    employment_status: str | None = None


class EmployeeUserLink(BaseModel):
    user_id: int


class EmployeeSelfUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


# ============================================================
# CREATE EMPLOYEE
# ADMIN + HR
# ============================================================

@router.post("/")
def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    # --------------------------------------------------------
    # Validate First Name
    # --------------------------------------------------------

    first_name = validate_name(
        employee_data.first_name,
        "First Name"
    )

    # --------------------------------------------------------
    # Validate Last Name
    # --------------------------------------------------------

    last_name = validate_name(
        employee_data.last_name,
        "Last Name"
    )

    # --------------------------------------------------------
    # Validate Designation
    # --------------------------------------------------------

    designation = validate_name(
        employee_data.designation,
        "Designation"
    )

    # --------------------------------------------------------
    # Validate Phone
    # --------------------------------------------------------

    phone = validate_phone(employee_data.phone)

    # --------------------------------------------------------
    # Clean Employee ID
    # Employee ID remains VARCHAR / string
    # --------------------------------------------------------

    employee_id = employee_data.employee_id.strip()

    if not employee_id:
        raise HTTPException(
            status_code=400,
            detail="Employee ID is required"
        )

    # --------------------------------------------------------
    # Clean Email
    # --------------------------------------------------------

    email = employee_data.email.strip()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required"
        )

    # --------------------------------------------------------
    # Check Department
    # --------------------------------------------------------

    department = (
        db.query(Department)
        .filter(Department.id == employee_data.department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # --------------------------------------------------------
    # Check Duplicate Employee ID
    # --------------------------------------------------------

    existing_employee = (
        db.query(Employee)
        .filter(Employee.employee_id == employee_id)
        .first()
    )

    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="Employee ID already exists"
        )

    # --------------------------------------------------------
    # Check Duplicate Email
    # --------------------------------------------------------

    existing_email = (
        db.query(Employee)
        .filter(Employee.email == email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Employee email already exists"
        )

    # --------------------------------------------------------
    # Create Employee
    # --------------------------------------------------------

    new_employee = Employee(
        employee_id=employee_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        department_id=employee_data.department_id,
        designation=designation,
        joining_date=employee_data.joining_date,
        employment_status=employee_data.employment_status
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return {
        "message": "Employee created successfully",
        "employee": {
            "id": new_employee.id,
            "employee_id": new_employee.employee_id,
            "first_name": new_employee.first_name,
            "last_name": new_employee.last_name,
            "email": new_employee.email,
            "phone": new_employee.phone,
            "department_id": new_employee.department_id,
            "designation": new_employee.designation,
            "joining_date": new_employee.joining_date,
            "employment_status": new_employee.employment_status
        }
    }


# ============================================================
# GET ALL EMPLOYEES
# ADMIN + HR
# ============================================================

@router.get("/")
def get_employees(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    employees = db.query(Employee).all()

    return employees


# ============================================================
# LINK USER TO EMPLOYEE
# ADMIN ONLY
# ============================================================

@router.put("/{employee_id}/link-user")
def link_user_to_employee(
    employee_id: int,
    link_data: EmployeeUserLink,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    # Find employee
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    # Find user
    user = (
        db.query(User)
        .filter(User.id == link_data.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Only employee-role users can be linked
    if user.role != "employee":
        raise HTTPException(
            status_code=400,
            detail="Only users with employee role can be linked to an employee"
        )

    # Check if user is already linked to another employee
    existing_employee = (
        db.query(Employee)
        .filter(
            Employee.user_id == link_data.user_id,
            Employee.id != employee_id
        )
        .first()
    )

    if existing_employee:
        raise HTTPException(
            status_code=400,
            detail="User is already linked to another employee"
        )

    # Check if employee is already linked
    if employee.user_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Employee is already linked to a user"
        )

    # Link user
    employee.user_id = user.id

    db.commit()
    db.refresh(employee)

    return {
        "message": "User linked to employee successfully",
        "employee_id": employee.id,
        "user_id": user.id,
        "username": user.username
    }


# ============================================================
# GET CURRENT EMPLOYEE PROFILE
# EMPLOYEE ONLY
# ============================================================

@router.get("/me")
def get_my_employee_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("employee"))
):
    employee = (
        db.query(Employee)
        .filter(Employee.user_id == current_user.id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not linked to this user"
        )

    return {
        "message": "Employee profile retrieved successfully",
        "employee": {
            "id": employee.id,
            "employee_id": employee.employee_id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "phone": employee.phone,
            "department_id": employee.department_id,
            "designation": employee.designation,
            "joining_date": employee.joining_date,
            "employment_status": employee.employment_status
        }
    }


# ============================================================
# UPDATE CURRENT EMPLOYEE PROFILE
# EMPLOYEE ONLY
# ============================================================

@router.put("/me")
def update_my_employee_profile(
    employee_data: EmployeeSelfUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("employee"))
):
    employee = (
        db.query(Employee)
        .filter(Employee.user_id == current_user.id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not linked to this user"
        )

    # --------------------------------------------------------
    # Update First Name
    # --------------------------------------------------------

    if employee_data.first_name is not None:
        employee.first_name = validate_name(
            employee_data.first_name,
            "First Name"
        )

    # --------------------------------------------------------
    # Update Last Name
    # --------------------------------------------------------

    if employee_data.last_name is not None:
        employee.last_name = validate_name(
            employee_data.last_name,
            "Last Name"
        )

    # --------------------------------------------------------
    # Update Phone
    # --------------------------------------------------------

    if employee_data.phone is not None:
        employee.phone = validate_phone(
            employee_data.phone
        )

    db.commit()
    db.refresh(employee)

    return {
        "message": "Employee profile updated successfully",
        "employee": {
            "id": employee.id,
            "employee_id": employee.employee_id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "phone": employee.phone,
            "department_id": employee.department_id,
            "designation": employee.designation,
            "joining_date": employee.joining_date,
            "employment_status": employee.employment_status
        }
    }


# ============================================================
# GET EMPLOYEE BY ID
# ADMIN + HR
# ============================================================

@router.get("/{employee_id}")
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return employee


# ============================================================
# UPDATE EMPLOYEE
# ADMIN + HR
# ============================================================

@router.put("/{employee_id}")
def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    # --------------------------------------------------------
    # Update Department
    # --------------------------------------------------------

    if employee_data.department_id is not None:
        department = (
            db.query(Department)
            .filter(
                Department.id == employee_data.department_id
            )
            .first()
        )

        if not department:
            raise HTTPException(
                status_code=404,
                detail="Department not found"
            )

        employee.department_id = employee_data.department_id

    # --------------------------------------------------------
    # Update First Name
    # --------------------------------------------------------

    if employee_data.first_name is not None:
        employee.first_name = validate_name(
            employee_data.first_name,
            "First Name"
        )

    # --------------------------------------------------------
    # Update Last Name
    # --------------------------------------------------------

    if employee_data.last_name is not None:
        employee.last_name = validate_name(
            employee_data.last_name,
            "Last Name"
        )

    # --------------------------------------------------------
    # Update Email
    # --------------------------------------------------------

    if employee_data.email is not None:
        email = employee_data.email.strip()

        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email cannot be empty"
            )

        existing_email = (
            db.query(Employee)
            .filter(
                Employee.email == email,
                Employee.id != employee_id
            )
            .first()
        )

        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Employee email already exists"
            )

        employee.email = email

    # --------------------------------------------------------
    # Update Phone
    # --------------------------------------------------------

    if employee_data.phone is not None:
        employee.phone = validate_phone(
            employee_data.phone
        )

    # --------------------------------------------------------
    # Update Designation
    # --------------------------------------------------------

    if employee_data.designation is not None:
        employee.designation = validate_name(
            employee_data.designation,
            "Designation"
        )

    # --------------------------------------------------------
    # Update Joining Date
    # --------------------------------------------------------

    if employee_data.joining_date is not None:
        employee.joining_date = employee_data.joining_date

    # --------------------------------------------------------
    # Update Employment Status
    # --------------------------------------------------------

    if employee_data.employment_status is not None:
        employee.employment_status = (
            employee_data.employment_status.strip()
        )

    db.commit()
    db.refresh(employee)

    return {
        "message": "Employee updated successfully",
        "employee": {
            "id": employee.id,
            "employee_id": employee.employee_id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "phone": employee.phone,
            "department_id": employee.department_id,
            "designation": employee.designation,
            "joining_date": employee.joining_date,
            "employment_status": employee.employment_status
        }
    }


# ============================================================
# DELETE EMPLOYEE
# ADMIN ONLY
# ============================================================

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    db.delete(employee)
    db.commit()

    return {
        "message": "Employee deleted successfully"
    }