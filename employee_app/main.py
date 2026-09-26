from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from database import Base, engine

from models.user import User
from models.employee import Employee
from models.department import Department
from models.attendance import Attendance
from models.salary import Salary

from routes.departments import router as department_router
from routes.employees import router as employee_router
from routes.auth import router as auth_router
from routes.test_auth import router as test_auth_router
from routes.role_test import router as role_test_router
from routes.attendance import router as attendance_router
from routes.salary import router as salary_router
from routes.dashboard import router as dashboard_router
from routes.users import router as users_router

# ---------------------------------------------------------
# Project directories
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# ---------------------------------------------------------
# Create database tables
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Employee Management System",
    description="Employee Management Application",
    version="1.0.0"
)


# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


# ---------------------------------------------------------
# Jinja2 templates
# ---------------------------------------------------------

templates = Jinja2Templates(
    directory=TEMPLATES_DIR
)


# ---------------------------------------------------------
# API routers
# ---------------------------------------------------------

app.include_router(department_router)
app.include_router(employee_router)
app.include_router(auth_router)
app.include_router(test_auth_router)
app.include_router(role_test_router)
app.include_router(attendance_router)
app.include_router(salary_router)
app.include_router(dashboard_router)
app.include_router(users_router)

# ---------------------------------------------------------
# Frontend pages
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request
        }
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "request": request
        }
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request
        }
    )


@app.get("/employees-page", response_class=HTMLResponse)
def employees_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="employees.html",
        context={
            "request": request
        }
    )


@app.get("/departments-page", response_class=HTMLResponse)
def departments_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="departments.html",
        context={
            "request": request
        }
    )


@app.get("/attendance-page", response_class=HTMLResponse)
def attendance_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="attendance.html",
        context={
            "request": request
        }
    )


@app.get("/payroll-page", response_class=HTMLResponse)
def payroll_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="payroll.html",
        context={
            "request": request
        }
    )


@app.get("/profile-page", response_class=HTMLResponse)
def profile_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "request": request
        }
    )

@app.get("/users-page", response_class=HTMLResponse)
def users_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={"request": request}
    )