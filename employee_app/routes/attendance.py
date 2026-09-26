from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.attendance import Attendance
from models.employee import Employee
from dependencies import require_roles


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)


# ============================================================
# REQUEST MODEL
# ============================================================

class AttendanceCreate(BaseModel):
    status: str = "Present"
    remarks: str | None = None


# ============================================================
# MARK ATTENDANCE
# EMPLOYEE ONLY
# ============================================================

@router.post("/me")
def mark_attendance(
    attendance_data: AttendanceCreate,
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

    existing_attendance = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date == today
        )
        .first()
    )

    if existing_attendance:
        raise HTTPException(
            status_code=400,
            detail="Attendance already marked for today"
        )

    allowed_statuses = ["Present", "Absent", "Leave"]

    if attendance_data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid attendance status"
        )

    attendance = Attendance(
        employee_id=employee.id,
        attendance_date=today,
        status=attendance_data.status,
        remarks=attendance_data.remarks
    )

    db.add(attendance)
    db.commit()
    db.refresh(attendance)

    return {
        "message": "Attendance marked successfully",
        "attendance": {
            "id": attendance.id,
            "employee_id": attendance.employee_id,
            "attendance_date": attendance.attendance_date,
            "status": attendance.status,
            "remarks": attendance.remarks
        }
    }


# ============================================================
# GET MY ATTENDANCE
# EMPLOYEE ONLY
# ============================================================

@router.get("/me")
def get_my_attendance(
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

    attendance_records = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id)
        .order_by(Attendance.attendance_date.desc())
        .all()
    )

    return attendance_records


# ============================================================
# GET ALL ATTENDANCE
# ADMIN + HR
# ============================================================

@router.get("/")
def get_all_attendance(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    attendance_records = (
        db.query(Attendance)
        .order_by(Attendance.attendance_date.desc())
        .all()
    )

    return attendance_records