"""Emergency script: lift every active block. Run: python unblock_all.py"""

from models.security import BlockedIP
from security_database import SecurityBase, SecuritySessionLocal, security_engine

SecurityBase.metadata.create_all(bind=security_engine)

db = SecuritySessionLocal()

try:
    count = (
        db.query(BlockedIP)
        .filter(BlockedIP.status == "ACTIVE")
        .update({"status": "UNBLOCKED"})
    )
    db.commit()
    print(f"Unblocked {count} IP block(s).")
finally:
    db.close()
