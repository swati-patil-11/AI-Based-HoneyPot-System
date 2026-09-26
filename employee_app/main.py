from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import Base, engine

from models.user import User
from models.employee import Employee
from models.department import Department
from models.attendance import Attendance

from routes.departments import router as department_router
from routes.employees import router as employee_router
from routes.auth import router as auth_router
from routes.test_auth import router as test_auth_router
from routes.role_test import router as role_test_router
from routes.attendance import router as attendance_router
from models.salary import Salary
from routes.salary import router as salary_router


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Employee Management System",
    description="Employee Management Application",
    version="1.0.0"
)


# ============================================================
# REGISTER ROUTERS
# ============================================================

app.include_router(department_router)
app.include_router(employee_router)
app.include_router(auth_router)
app.include_router(test_auth_router)
app.include_router(role_test_router)
app.include_router(attendance_router)
app.include_router(salary_router)

# ============================================================
# HOME
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Employee Management System</title>
    </head>
    <body>
        <h1>Employee Management System</h1>
        <p>Application is running successfully.</p>
        <p>Database is connected.</p>
        <p>Department module is ready.</p>
        <p>Employee module is ready.</p>
        <p>Attendance module is ready.</p>
    </body>
    </html>
    """