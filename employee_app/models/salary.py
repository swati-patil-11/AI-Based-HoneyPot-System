from sqlalchemy import Column, Integer, Float, String, ForeignKey
from database import Base


class Salary(Base):
    __tablename__ = "salaries"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        unique=True,
        nullable=False
    )

    basic_salary = Column(
        Float,
        nullable=False
    )

    allowances = Column(
        Float,
        nullable=False,
        default=0
    )

    deductions = Column(
        Float,
        nullable=False,
        default=0
    )

    currency = Column(
        String(10),
        nullable=False,
        default="INR"
    )