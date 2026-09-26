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
    employee_id: int
    basic_salary: float
    allowances: float = 0
    deductions: float = 0
    currency: str = "INR"


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
    employee = (
        db.query(Employee)
        .filter(Employee.id == salary_data.employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    existing_salary = (
        db.query(Salary)
        .filter(Salary.employee_id == salary_data.employee_id)
        .first()
    )

    if existing_salary:
        raise HTTPException(
            status_code=400,
            detail="Salary record already exists for this employee"
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
        employee_id=salary_data.employee_id,
        basic_salary=salary_data.basic_salary,
        allowances=salary_data.allowances,
        deductions=salary_data.deductions,
        currency=salary_data.currency
    )

    db.add(salary)
    db.commit()
    db.refresh(salary)

    return {
        "message": "Salary record created successfully",
        "salary": {
            "id": salary.id,
            "employee_id": salary.employee_id,
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
        .join(Employee, Salary.employee_id == Employee.id)
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
            "salary_id": salary.id,
            "employee_id": employee.id,
            "employee_code": employee.employee_id,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "basic_salary": salary.basic_salary,
            "allowances": salary.allowances,
            "deductions": salary.deductions,
            "net_salary": net_salary,
            "currency": salary.currency
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
        .filter(Employee.user_id == current_user.id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not linked to this user"
        )

    salary = (
        db.query(Salary)
        .filter(Salary.employee_id == employee.id)
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
        "employee_id": employee.employee_id,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "basic_salary": salary.basic_salary,
        "allowances": salary.allowances,
        "deductions": salary.deductions,
        "net_salary": net_salary,
        "currency": salary.currency
    }