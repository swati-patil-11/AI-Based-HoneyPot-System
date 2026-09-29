from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.salary import Salary
from models.employee import Employee
from dependencies import require_roles


router = APIRouter(
    prefix="/salary",
    tags=["Salary"]
)


# ============================================================
# REQUEST MODEL
# ============================================================

class SalaryCreate(BaseModel):
    employee_id: str
    basic_salary: float
    allowances: float = 0
    deductions: float = 0
    currency: str = "INR"


# ============================================================
# FIND EMPLOYEE
# Employee Code is preferred.
#
# Example:
# EMP001
# EMP002
#
# Numeric database IDs are also accepted for compatibility.
# ============================================================

def find_employee(
    employee_reference: str,
    db: Session
):
    reference = employee_reference.strip()

    if not reference:
        return None

    # First try Employee Code
    employee = (
        db.query(Employee)
        .filter(Employee.employee_id == reference.upper())
        .first()
    )

    if employee:
        return employee

    # Backward compatibility:
    # allow database ID such as 1 or 2
    if reference.isdigit():

        employee = (
            db.query(Employee)
            .filter(Employee.id == int(reference))
            .first()
        )

        if employee:
            return employee

    return None


# ============================================================
# CREATE SALARY
# ADMIN + HR
# ============================================================

@router.post("/")
def create_salary(
    salary_data: SalaryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):

    employee = find_employee(
        salary_data.employee_id,
        db
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found. Enter a valid Employee Code such as EMP001."
        )


    existing_salary = (
        db.query(Salary)
        .filter(
            Salary.employee_id == employee.id
        )
        .first()
    )

    if existing_salary:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Salary record already exists for "
                f"{employee.employee_id} - "
                f"{employee.first_name} {employee.last_name}"
            )
        )


    if salary_data.basic_salary < 0:
        raise HTTPException(
            status_code=400,
            detail="Basic salary cannot be negative"
        )


    if salary_data.allowances < 0:
        raise HTTPException(
            status_code=400,
            detail="Allowances cannot be negative"
        )


    if salary_data.deductions < 0:
        raise HTTPException(
            status_code=400,
            detail="Deductions cannot be negative"
        )


    net_salary = (
        salary_data.basic_salary
        + salary_data.allowances
        - salary_data.deductions
    )


    if net_salary < 0:
        raise HTTPException(
            status_code=400,
            detail="Net salary cannot be negative"
        )


    salary = Salary(
        employee_id=employee.id,
        basic_salary=salary_data.basic_salary,
        allowances=salary_data.allowances,
        deductions=salary_data.deductions,
        currency=salary_data.currency.upper()
    )


    db.add(salary)
    db.commit()
    db.refresh(salary)


    return {
        "message": "Salary record created successfully",
        "salary": {
            "id": salary.id,
            "employee_id": employee.id,
            "employee_code": employee.employee_id,
            "employee_name": (
                f"{employee.first_name} "
                f"{employee.last_name}"
            ),
            "basic_salary": salary.basic_salary,
            "allowances": salary.allowances,
            "deductions": salary.deductions,
            "net_salary": net_salary,
            "currency": salary.currency
        }
    }


# ============================================================
# GET ALL SALARIES
# ADMIN + HR
# ============================================================

@router.get("/")
def get_all_salaries(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):

    records = (
        db.query(Salary, Employee)
        .join(
            Employee,
            Salary.employee_id == Employee.id
        )
        .all()
    )


    result = []


    for salary, employee in records:

        net_salary = (
            salary.basic_salary
            + salary.allowances
            - salary.deductions
        )


        result.append({

            "salary_id":
                salary.id,

            "employee_id":
                employee.id,

            "employee_code":
                employee.employee_id,

            "employee_name":
                (
                    f"{employee.first_name} "
                    f"{employee.last_name}"
                ),

            "basic_salary":
                salary.basic_salary,

            "allowances":
                salary.allowances,

            "deductions":
                salary.deductions,

            "net_salary":
                net_salary,

            "currency":
                salary.currency
        })


    return result


# ============================================================
# GET MY SALARY
# EMPLOYEE ONLY
# ============================================================

@router.get("/me")
def get_my_salary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("employee"))
):

    employee = (
        db.query(Employee)
        .filter(
            Employee.user_id == current_user.id
        )
        .first()
    )


    if not employee:

        raise HTTPException(
            status_code=404,
            detail="Employee profile not linked to this user"
        )


    salary = (
        db.query(Salary)
        .filter(
            Salary.employee_id == employee.id
        )
        .first()
    )


    if not salary:

        raise HTTPException(
            status_code=404,
            detail="Salary record not found"
        )


    net_salary = (
        salary.basic_salary
        + salary.allowances
        - salary.deductions
    )


    return {

        "employee_id":
            employee.employee_id,

        "employee_name":
            (
                f"{employee.first_name} "
                f"{employee.last_name}"
            ),

        "basic_salary":
            salary.basic_salary,

        "allowances":
            salary.allowances,

        "deductions":
            salary.deductions,

        "net_salary":
            net_salary,

        "currency":
            salary.currency
    }