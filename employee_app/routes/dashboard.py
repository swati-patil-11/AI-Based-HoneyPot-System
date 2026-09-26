from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_roles
from models.employee import Employee
from models.department import Department
from models.attendance import Attendance
from models.salary import Salary


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


# ============================================================
# ADMIN / HR DASHBOARD
# ============================================================

@router.get("/admin")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    total_employees = db.query(Employee).count()

    active_employees = (
        db.query(Employee)
        .filter(Employee.employment_status == "Active")
        .count()
    )

    total_departments = db.query(Department).count()

    today = date.today()

    present_today = (
        db.query(Attendance)
        .filter(
            Attendance.attendance_date == today,
            Attendance.status == "Present"
        )
        .count()
    )

    absent_today = (
        db.query(Attendance)
        .filter(
            Attendance.attendance_date == today,
            Attendance.status == "Absent"
        )
        .count()
    )

    leave_today = (
        db.query(Attendance)
        .filter(
            Attendance.attendance_date == today,
            Attendance.status == "Leave"
        )
        .count()
    )

    total_salary_records = db.query(Salary).count()

    salaries = db.query(Salary).all()

    total_payroll = sum(
        salary.basic_salary
        + salary.allowances
        - salary.deductions
        for salary in salaries
    )

    return {
        "dashboard": {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "total_departments": total_departments,
            "attendance_today": {
                "present": present_today,
                "absent": absent_today,
                "leave": leave_today
            },
            "total_salary_records": total_salary_records,
            "total_payroll": total_payroll,
            "currency": "INR"
        }
    }


# ============================================================
# EMPLOYEE DASHBOARD
# ============================================================

@router.get("/me")
def employee_dashboard(
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

    today = date.today()

    today_attendance = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date == today
        )
        .first()
    )

    salary = (
        db.query(Salary)
        .filter(Salary.employee_id == employee.id)
        .first()
    )

    net_salary = None

    if salary:
        net_salary = (
            salary.basic_salary
            + salary.allowances
            - salary.deductions
        )

    return {
        "employee": {
            "employee_id": employee.employee_id,
            "name": f"{employee.first_name} {employee.last_name}",
            "email": employee.email,
            "designation": employee.designation,
            "department_id": employee.department_id,
            "employment_status": employee.employment_status
        },
        "today_attendance": (
            {
                "status": today_attendance.status,
                "remarks": today_attendance.remarks
            }
            if today_attendance
            else None
        ),
        "salary": (
            {
                "basic_salary": salary.basic_salary,
                "allowances": salary.allowances,
                "deductions": salary.deductions,
                "net_salary": net_salary,
                "currency": salary.currency
            }
            if salary
            else None
        )
    }