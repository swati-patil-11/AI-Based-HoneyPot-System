import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from database import Base, engine
from security_database import SecurityBase, security_engine

from models.user import User
from models.employee import Employee
from models.department import Department
from models.attendance import Attendance
from models.salary import Salary
from models import security as security_models  # noqa: F401 (registers security tables)

from routes.departments import router as department_router
from routes.employees import router as employee_router
from routes.auth import router as auth_router
from routes.test_auth import router as test_auth_router
from routes.role_test import router as role_test_router
from routes.attendance import router as attendance_router
from routes.salary import router as salary_router
from routes.dashboard import router as dashboard_router
from routes.users import router as users_router
from routes.admin_security import router as admin_security_router, handle_admin_ws
from routes.trap import router as trap_router
from services import blocking_service, system_metrics_service, trap_service

from middleware.detection import DetectionMiddleware
from middleware.ip_blocker import IPBlockerMiddleware
from middleware.request_logger import RequestLoggerMiddleware

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
SecurityBase.metadata.create_all(bind=security_engine)
trap_service.expire_all_open_sessions()   # sessions left open by a stopped server


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(_app):
    # background job: marks finished IP blocks as EXPIRED
    cleanup_task = asyncio.create_task(blocking_service.cleanup_loop())
    # background job: samples CPU/memory and system health (Phase 11)
    metrics_task = asyncio.create_task(system_metrics_service.metrics_loop())

    try:
        yield
    finally:
        cleanup_task.cancel()
        metrics_task.cancel()


app = FastAPI(
    title="Employee Management System",
    description="Employee Management Application",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(admin_security_router)
app.include_router(trap_router)


# ---------------------------------------------------------
# Security middleware
# ---------------------------------------------------------
# Starlette: the LAST middleware added is the OUTERMOST one.
# We want:  request_logger (outer) -> ip_blocker -> detection -> routes
# so the logger also records requests that the blocker rejects.

app.add_middleware(DetectionMiddleware)
app.add_middleware(IPBlockerMiddleware)
app.add_middleware(RequestLoggerMiddleware)

# ---------------------------------------------------------
# WebSockets (Phase 11)
# ---------------------------------------------------------

@app.websocket("/ws/admin")
async def ws_admin_endpoint(websocket: WebSocket, token: str | None = None):
    await handle_admin_ws(websocket, token)


# ---------------------------------------------------------
# Frontend pages
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
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


# ---------------------------------------------------------
# Security Dashboard (Phase 12)
# ---------------------------------------------------------

@app.get("/admin/security-dashboard", response_class=HTMLResponse)
@app.get("/security-dashboard", response_class=HTMLResponse)
def security_dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin/security_dashboard.html",
        context={"request": request}
    )
