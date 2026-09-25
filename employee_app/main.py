from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import Base, engine
from models.user import User
from models.employee import Employee
from models.department import Department

from routes.departments import router as department_router
from routes.employees import router as employee_router
from routes.auth import router as auth_router
from routes.test_auth import router as test_auth_router
from routes.role_test import router as role_test_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Employee Management System",
    description="Employee Management Application",
    version="1.0.0"
)

#register


app.include_router(department_router)
app.include_router(employee_router)
app.include_router(auth_router)
app.include_router(test_auth_router)
app.include_router(role_test_router)



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
    </body>
    </html>
    """