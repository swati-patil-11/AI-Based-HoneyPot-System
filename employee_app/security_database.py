"""
Separate SQLite database for all security data.

Why a separate file?
    employee.db  -> the real, protected data
    security.db  -> logs, blocks, trap sessions, metrics, experiment runs

The trap and the detector can never touch real employee data through this
connection, and "SecurityBase" keeps these tables out of employee.db.
"""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

SECURITY_DATABASE_FILE = DATABASE_DIR / "security.db"
SECURITY_DATABASE_URL = f"sqlite:///{SECURITY_DATABASE_FILE.as_posix()}"


security_engine = create_engine(
    SECURITY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15}
)


@event.listens_for(security_engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record):
    # WAL lets one writer and many readers work at the same time,
    # which avoids "database is locked" under the attacker's load.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SecuritySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=security_engine
)

SecurityBase = declarative_base()


def get_security_db():
    db = SecuritySessionLocal()

    try:
        yield db
    finally:
        db.close()


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (SQLite stores no timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_experiment_run_schema(engine):
    """Ensures experiment_runs table has all Phase 13 columns."""
    with engine.connect() as conn:
        try:
            res = conn.execute(text("PRAGMA table_info(experiment_runs)"))
            existing = [row[1] for row in res.fetchall()]
            if not existing:
                return

            columns = [
                ("trap_enabled", "BOOLEAN DEFAULT 0"),
                ("total_requests", "INTEGER DEFAULT 0"),
                ("total_tokens", "INTEGER DEFAULT 0"),
                ("real_records_served", "INTEGER DEFAULT 0"),
                ("fake_records_served", "INTEGER DEFAULT 0"),
                ("time_to_first_block_sec", "FLOAT"),
                ("peak_cpu_percent", "FLOAT"),
                ("peak_memory_percent", "FLOAT"),
                ("avg_cpu_percent", "FLOAT"),
                ("avg_memory_percent", "FLOAT"),
                ("stop_reason", "VARCHAR(50)"),
                ("simulator_report_json", "TEXT"),
            ]
            for col_name, col_type in columns:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE experiment_runs ADD COLUMN {col_name} {col_type}"))
            conn.commit()
        except Exception as e:
            print(f"[security_database] Schema check: {e}")


ensure_experiment_run_schema(security_engine)

