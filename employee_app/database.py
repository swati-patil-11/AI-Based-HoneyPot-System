from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Get the employee_app folder
BASE_DIR = Path(__file__).resolve().parent

# Database folder
DATABASE_DIR = BASE_DIR / "database"

# Make sure database folder exists
DATABASE_DIR.mkdir(exist_ok=True)

# Full database path
DATABASE_FILE = DATABASE_DIR / "employee.db"

# SQLite connection URL
DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()