"""
Synthetic (fake) employee records for the trap.

SAFETY RULE: this file never imports the Employee model and never opens
employee.db. Fake data is made from a seeded random generator only, so
the trap cannot leak real data.

The same id always gives the same fake record (seeded per id). That keeps
the deception consistent: asking twice for /employees/7 returns the same
person, like a real database would.

For YOUR analysis, every synthetic record can be recognised by its email
domain (TRAP_EMAIL_DOMAIN in config.py).
"""

import json
import zlib
from datetime import date, timedelta

from faker import Faker

import config as cfg


_fake = Faker("en_IN")

# Same shape as the real data (the real app has departments 1-3).
DEPARTMENT_IDS = (1, 2, 3)

DESIGNATIONS = (
    "System Administrator", "Network Engineer", "IT Support Specialist",
    "Security Analyst", "SOC Engineer", "Penetration Tester",
    "Software Developer", "QA Engineer", "DevOps Engineer",
)


def make_record(record_id: int) -> dict:
    _fake.seed_instance(cfg.TRAP_SEED + record_id)

    first = _fake.first_name()
    last = _fake.last_name()

    return {
        "employee_id": f"EMP{20000 + record_id}",
        "email": f"{first}.{last}.{record_id}@{cfg.TRAP_EMAIL_DOMAIN}".lower(),
        "first_name": first,
        "department_id": _fake.random_element(DEPARTMENT_IDS),
        "joining_date": (
            date(2018, 1, 1) + timedelta(days=_fake.random_int(0, 3000))
        ).isoformat(),
        "user_id": None,
        "id": record_id,
        "last_name": last,
        "phone": _fake.numerify("##########"),
        "designation": _fake.random_element(DESIGNATIONS),
        "employment_status": _fake.random_element(
            ["Active"] * 12 + ["Inactive"]
        ),
    }


def record_size(record: dict) -> int:
    return len(json.dumps(record).encode())


def page_ids(page: int, size: int) -> list[int]:
    start = (page - 1) * size + 1
    return list(range(start, start + size))


def search_ids(query: str, page: int, size: int) -> list[int]:
    """Fake search hits: the same query always returns the same people."""
    base = 1000 + (zlib.crc32(query.lower().encode()) % 40000)
    start = base + (page - 1) * size
    return list(range(start, start + size))
