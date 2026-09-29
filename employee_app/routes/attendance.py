from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
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
# MARK OWN ATTENDANCE
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

    allowed_statuses = [
        "Present",
        "Absent",
        "Leave"
    ]

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
        .filter(
            Attendance.employee_id == employee.id
        )
        .order_by(
            Attendance.attendance_date.desc()
        )
        .all()
    )

    return {
        "attendance": attendance_records
    }


# ============================================================
# GET ALL ATTENDANCE
# ADMIN + HR
#
# Optional filters:
# attendance_date=YYYY-MM-DD
# employee_id=1
# ============================================================

@router.get("/")
def get_all_attendance(
    attendance_date: date | None = Query(
        default=None
    ),
    employee_id: int | None = Query(
        default=None,
        ge=1
    ),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("admin", "hr")
    )
):

    # --------------------------------------------------------
    # Build query
    # --------------------------------------------------------

    query = (
        db.query(
            Attendance,
            Employee
        )
        .join(
            Employee,
            Attendance.employee_id == Employee.id
        )
    )

    # --------------------------------------------------------
    # Date filter
    # --------------------------------------------------------

    if attendance_date is not None:
        query = query.filter(
            Attendance.attendance_date ==
            attendance_date
        )

    # --------------------------------------------------------
    # Employee filter
    # --------------------------------------------------------

    if employee_id is not None:
        query = query.filter(
            Attendance.employee_id ==
            employee_id
        )

    # --------------------------------------------------------
    # Latest attendance first
    # --------------------------------------------------------

    query = query.order_by(
        Attendance.attendance_date.desc(),
        Attendance.id.desc()
    )

    results = query.all()

    # --------------------------------------------------------
    # Format response for frontend
    # --------------------------------------------------------

    attendance_records = []

    for attendance, employee in results:

        attendance_records.append({
            "attendance_id": attendance.id,

            "employee_id": employee.id,

            "employee_code": employee.employee_id,

            "employee_name": (
                f"{employee.first_name} "
                f"{employee.last_name}"
            ).strip(),

            "attendance_date":
                attendance.attendance_date,

            "status":
                attendance.status,

            "remarks":
                attendance.remarks
        })

    return attendance_records