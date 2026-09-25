from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.department import Department
from dependencies import require_roles


router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


# =========================
# Request Models
# =========================

class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: str | None = None


# =========================
# Create Department
# Admin Only
# =========================

@router.post("/")
def create_department(
    department: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    # Check duplicate department
    existing_department = (
        db.query(Department)
        .filter(Department.name == department.name)
        .first()
    )

    if existing_department:
        raise HTTPException(
            status_code=400,
            detail="Department already exists"
        )

    # Create department
    new_department = Department(
        name=department.name,
        description=department.description,
        is_active="Active"
    )

    db.add(new_department)
    db.commit()
    db.refresh(new_department)

    return {
        "message": "Department created successfully",
        "department": {
            "id": new_department.id,
            "name": new_department.name,
            "description": new_department.description,
            "is_active": new_department.is_active
        }
    }


# =========================
# Get All Departments
# Admin + HR
# =========================

@router.get("/")
def get_departments(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    departments = db.query(Department).all()

    return departments


# =========================
# Get Department By ID
# Admin + HR
# =========================

@router.get("/{department_id}")
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "hr"))
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    return department


# =========================
# Update Department
# Admin Only
# =========================

@router.put("/{department_id}")
def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Check duplicate name
    if department_data.name is not None:

        existing_department = (
            db.query(Department)
            .filter(
                Department.name == department_data.name,
                Department.id != department_id
            )
            .first()
        )

        if existing_department:
            raise HTTPException(
                status_code=400,
                detail="Department name already exists"
            )

        department.name = department_data.name

    # Update description
    if department_data.description is not None:
        department.description = department_data.description

    # Update status
    if department_data.is_active is not None:
        department.is_active = department_data.is_active

    db.commit()
    db.refresh(department)

    return {
        "message": "Department updated successfully",
        "department": department
    }


# =========================
# Delete Department
# Admin Only
# =========================

@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    db.delete(department)
    db.commit()

    return {
        "message": "Department deleted successfully"
    }