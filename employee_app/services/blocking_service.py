"""
Temporary IP blocking.

Phase 5: create / check / expire / unblock.
Phase 9: automatic blocks with escalation, and a background cleanup job.

Rules:
  - A block always has an expires_at. There is NO permanent ban.
  - Escalation: 1st violation -> 5 min, 2nd -> 30 min, 3rd+ -> 120 min
    (BLOCK_DURATIONS_MINUTES in config.py).
  - A block an admin lifted early (UNBLOCKED) does not count as a
    violation: the admin decided it was a false alarm.
  - Violations older than VIOLATION_MEMORY_HOURS are forgotten.
  - After a block expires the IP is monitored again from scratch.
"""

import asyncio
import threading
import time
from collections import deque
from datetime import timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

import config as cfg
from models.security import BlockedIP, TrapSession
from security_database import SecuritySessionLocal, utcnow
from services import detection_service, trap_service
from services.ws_manager import manager as ws_manager


def _broadcast_block(block: BlockedIP):
    remaining = 0
    if block.status == "ACTIVE" and block.expires_at:
        remaining = max(0, int((block.expires_at - utcnow()).total_seconds()))

    ws_manager.broadcast_sync(
        "block_event",
        {
            "id": block.id,
            "ip_address": block.ip_address,
            "status": block.status,
            "reason": block.reason,
            "created_at": block.created_at.isoformat() + "Z" if block.created_at else None,
            "expires_at": block.expires_at.isoformat() + "Z" if block.expires_at else None,
            "seconds_remaining": remaining,
            "created_by": block.created_by,
            "violation_count": block.violation_count,
            "trap_session_id": block.trap_session_id,
        },
    )


_refusals: dict[str, deque] = {}
_lock = threading.Lock()


# ---------------------------------------------------------
# basic operations (Phase 5)
# ---------------------------------------------------------

def get_active_block(db: Session, ip_address: str) -> BlockedIP | None:
    """
    Return the active block for this IP, or None.
    Blocks that have passed expires_at are marked EXPIRED here,
    so expiry happens automatically on the next request.
    """
    now = utcnow()

    blocks = (
        db.query(BlockedIP)
        .filter(
            BlockedIP.ip_address == ip_address,
            BlockedIP.status == "ACTIVE"
        )
        .all()
    )

    active = None

    for block in blocks:
        if block.expires_at <= now:
            block.status = "EXPIRED"
        else:
            active = block

    db.commit()

    return active


def create_block(
    db: Session,
    ip_address: str,
    minutes: int,
    reason: str = "",
    created_by: str = "system",
    trap_session_id: int | None = None,
    violation_count: int | None = None,
) -> BlockedIP:
    if violation_count is None:
        violation_count = (
            db.query(BlockedIP).filter(BlockedIP.ip_address == ip_address).count() + 1
        )

    block = BlockedIP(
        ip_address=ip_address,
        reason=reason,
        status="ACTIVE",
        created_at=utcnow(),
        expires_at=utcnow() + timedelta(minutes=minutes),
        created_by=created_by,
        violation_count=violation_count,
        trap_session_id=trap_session_id,
    )

    db.add(block)
    db.commit()
    db.refresh(block)

    _broadcast_block(block)

    return block


def unblock(db: Session, block_id: int, admin_name: str) -> BlockedIP | None:
    block = db.query(BlockedIP).filter(BlockedIP.id == block_id).first()

    if not block:
        return None

    block.status = "UNBLOCKED"
    block.created_by = f"{block.created_by} (unblocked by {admin_name})"
    db.commit()
    db.refresh(block)

    _broadcast_block(block)

    return block


# ---------------------------------------------------------
# automatic blocking (Phase 9)
# ---------------------------------------------------------

def next_violation(db: Session, ip_address: str) -> tuple[int, int]:
    """Returns (violation_number, block_minutes) for this IP's next block."""
    since = utcnow() - timedelta(hours=cfg.VIOLATION_MEMORY_HOURS)

    earlier = (
        db.query(BlockedIP)
        .filter(
            BlockedIP.ip_address == ip_address,
            BlockedIP.created_by.like("system%"),
            BlockedIP.status != "UNBLOCKED",
            BlockedIP.created_at >= since,
        )
        .count()
    )

    durations = cfg.BLOCK_DURATIONS_MINUTES
    minutes = durations[min(earlier, len(durations) - 1)]

    return earlier + 1, minutes


def _count_refusal(ip_address: str) -> int:
    """Count one refusal inside the sliding window; returns the count."""
    now = time.monotonic()
    cutoff = now - cfg.BLOCK_COUNT_WINDOW_SECONDS

    with _lock:
        times = _refusals.setdefault(ip_address, deque())
        times.append(now)

        while times and times[0] < cutoff:
            times.popleft()

        return len(times)


def register_trap_refusal(ip_address: str) -> BlockedIP | None:
    """
    Call this every time the trap answers 429 to an IP.
    Creates an escalated temporary block once the IP has kept asking
    more than BLOCK_AFTER_TRAP_REQUESTS times. Returns the new block or None.
    """
    if not cfg.BLOCKING_ENABLED or ip_address in cfg.BLOCK_ALLOWLIST:
        return None

    count = _count_refusal(ip_address)

    if count <= cfg.BLOCK_AFTER_TRAP_REQUESTS:
        return None

    db = SecuritySessionLocal()

    try:
        if get_active_block(db, ip_address):
            return None

        violation, minutes = next_violation(db, ip_address)

        session = (
            db.query(TrapSession)
            .filter(TrapSession.ip_address == ip_address)
            .order_by(TrapSession.id.desc())
            .first()
        )

        block = create_block(
            db,
            ip_address=ip_address,
            minutes=minutes,
            reason=(
                f"Kept requesting after the trap ({count} refused requests). "
                f"Violation #{violation}."
            ),
            created_by="system",
            trap_session_id=session.id if session else None,
            violation_count=violation,
        )

        if session and session.status == "TRAPPED":
            trap_service.finish_session(db, session.id, "COMPLETED")

        # start from scratch after the block
        with _lock:
            _refusals.pop(ip_address, None)

        detection_service.reset(ip_address)
        trap_service.forget_ip(ip_address)

        return block

    finally:
        db.close()


# ---------------------------------------------------------
# background cleanup
# ---------------------------------------------------------

def expire_old_blocks() -> int:
    """Mark every finished block as EXPIRED. Returns how many changed."""
    db = SecuritySessionLocal()

    try:
        changed = (
            db.query(BlockedIP)
            .filter(BlockedIP.status == "ACTIVE", BlockedIP.expires_at <= utcnow())
            .update({"status": "EXPIRED"})
        )
        db.commit()
        return changed
    finally:
        db.close()


async def cleanup_loop():
    """Runs for the whole life of the server (started in main.py)."""
    while True:
        try:
            await run_in_threadpool(expire_old_blocks)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"[blocking_service] cleanup error: {error}")

        await asyncio.sleep(cfg.BLOCK_CLEANUP_INTERVAL_SECONDS)


def reset_counters():
    with _lock:
        _refusals.clear()
