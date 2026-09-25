from sqlalchemy import Column, Integer, String, Date, ForeignKey
from database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    first_name = Column(
        String(50),
        nullable=False
    )

    last_name = Column(
        String(50),
        nullable=False
    )

    email = Column(
        String(100),
        unique=True,
        nullable=False
    )

    phone = Column(
        String(20),
        nullable=True
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False
    )

    designation = Column(
        String(50),
        nullable=False
    )

    joining_date = Column(
        Date,
        nullable=False
    )

    employment_status = Column(
        String(20),
        nullable=False,
        default="Active"
    )

    # Connect Employee with User account
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=True
    )