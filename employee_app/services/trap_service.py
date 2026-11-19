"""
Trap sessions and limits.

A trap session is opened when a flagged source asks for employee data.
From then on that source gets synthetic records only, under hard limits:

    MAX_TRAP_RECORDS       records per session
    MAX_TRAP_SESSION_TIME  seconds per session
    MAX_RESPONSE_SIZE      bytes per response
    MAX_SYNTHETIC_RECORD_RATE  records per second (streaming)
    MAX_ACTIVE_TRAPS       sessions open at once (whole server)

Settings are read from config at call time, so experiments can change them.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import config as cfg
from models.security import TrapMetric, TrapSession
from security_database import SecuritySessionLocal, utcnow
from services import synthetic_data_service as synthetic
from services import token_service
from services.ws_manager import manager as ws_manager


def log_fake_trap_data(session_id: int, ip: str, endpoint: str, records: list[dict], tokens: int = 0):
    """
    Saves generated synthetic (fake) records to dedicated files in FAKE_LOGS_DIR.
    Ensures that whenever the trap is active, fake logs are recorded in newly generated files.
    """
    try:
        os.makedirs(cfg.FAKE_LOGS_DIR, exist_ok=True)
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(cfg.FAKE_LOGS_DIR, f"fake_trap_session_{session_id}_{now_str}.json")

        entry = {
            "session_id": session_id,
            "ip_address": ip,
            "endpoint": endpoint,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "records_count": len(records),
            "tokens": tokens,
            "fake_records": records,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)

        log_file = os.path.join(cfg.FAKE_LOGS_DIR, "trap_fake_activity.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f"[{entry['timestamp']}] [TRAP ACTIVE] IP: {ip} | Session: #{session_id} | "
                f"Endpoint: {endpoint} | Fake Records: {len(records)} | Tokens: {tokens} | File: {file_path}\n"
            )
    except Exception as exc:
        print(f"[trap_service] Error writing fake log file: {exc}")


ITEM_PATH = re.compile(r"^/employees/(\d+)$")

_sticky: dict[str, float] = {}      # ip -> keep trapping until (monotonic time)
_cooldown_floor = None              # sessions that ended before this are ignored


@dataclass
class TrapReply:
    status: int
    body: object
    headers: dict = field(default_factory=dict)


# ---------------------------------------------------------
# which requests does the trap answer?
# ---------------------------------------------------------

def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def classify_request(method: str, path: str, params) -> dict | None:
    """
    Decide if a request is one the trap can answer.
    Covers GET /employees/, /employees/search, /employees/{id}, and /salary/.
    Everything else (including /employees/me and the HTML pages)
    is left alone. Returns None when the request should go to the real app.
    """
    if method != "GET":
        return None

    clean = path.rstrip("/") or "/"

    page = _int(params.get("page"), 1)
    size = _int(params.get("size"), 20)

    if clean == "/salary":
        return {"kind": "salary", "page": page, "size": size}

    if page < 1 or not 1 <= size <= 100:
        return None                      # the real endpoint will answer 422

    if clean == "/employees":
        return {"kind": "list", "page": page, "size": size}

    if clean == "/employees/search":
        query = (params.get("q") or "").strip()
        if not query:
            return None
        return {"kind": "search", "query": query[:50], "page": page, "size": size}

    match = ITEM_PATH.match(clean)
    if match and int(match.group(1)) >= 1:
        return {"kind": "item", "item_id": int(match.group(1))}

    return None


# ---------------------------------------------------------
# sessions
# ---------------------------------------------------------

def is_sticky(ip: str) -> bool:
    """A trapped IP stays trapped even if its score drops for a moment."""
    until = _sticky.get(ip)

    if until and until > time.monotonic():
        return True

    _sticky.pop(ip, None)
    return False


def forget_ip(ip: str):
    """Stop treating this IP as trapped (used when it gets blocked)."""
    _sticky.pop(ip, None)


def expire_stale_sessions(db: Session):
    cutoff = utcnow() - timedelta(seconds=cfg.MAX_TRAP_SESSION_TIME)

    db.query(TrapSession).filter(
        TrapSession.status == "TRAPPED",
        TrapSession.started_at < cutoff,
    ).update({"status": "EXPIRED", "ended_at": utcnow()})

    db.commit()


def expire_all_open_sessions():
    """Run at startup: sessions left open by a stopped server can't continue."""
    db = SecuritySessionLocal()

    try:
        db.query(TrapSession).filter(TrapSession.status == "TRAPPED").update(
            {"status": "EXPIRED", "ended_at": utcnow()}
        )
        db.commit()
    finally:
        db.close()


def open_or_continue_session(db: Session, ip: str):
    """Returns (session, None) or (None, reason_for_refusal)."""
    expire_stale_sessions(db)

    session = (
        db.query(TrapSession)
        .filter(TrapSession.ip_address == ip, TrapSession.status == "TRAPPED")
        .order_by(TrapSession.id.desc())
        .first()
    )

    if session:
        return session, None

    last = (
        db.query(TrapSession)
        .filter(
            TrapSession.ip_address == ip,
            TrapSession.status.in_(("COMPLETED", "EXPIRED")),
        )
        .order_by(TrapSession.id.desc())
        .first()
    )

    if last and last.ended_at:
        cooldown_ends = last.ended_at + timedelta(seconds=cfg.TRAP_COOLDOWN_SECONDS)
        ignored = _cooldown_floor is not None and last.ended_at <= _cooldown_floor

        if cooldown_ends > utcnow() and not ignored:
            return None, int((cooldown_ends - utcnow()).total_seconds()) + 1

    open_now = db.query(TrapSession).filter(TrapSession.status == "TRAPPED").count()

    if open_now >= cfg.MAX_ACTIVE_TRAPS:
        return None, 30

    session = TrapSession(ip_address=ip, status="TRAPPED")
    db.add(session)
    db.commit()
    db.refresh(session)

    _sticky[ip] = time.monotonic() + cfg.MAX_TRAP_SESSION_TIME + cfg.TRAP_COOLDOWN_SECONDS

    ws_manager.broadcast_sync(
        "trap_event",
        {
            "action": "started",
            "session_id": session.id,
            "ip_address": session.ip_address,
            "status": session.status,
            "records_served": session.records_served,
            "tokens_served": session.tokens_served,
        },
    )

    return session, None


def finish_session(db: Session, session_id: int, status: str):
    db.query(TrapSession).filter(TrapSession.id == session_id).update(
        {"status": status, "ended_at": utcnow()}
    )
    db.commit()

    ws_manager.broadcast_sync(
        "trap_event",
        {
            "action": "finished",
            "session_id": session_id,
            "status": status,
        },
    )


def add_progress(
    db: Session,
    session_id: int,
    records: int,
    size_bytes: int,
    tokens: int = 0,
    response_ms: float | None = None,
):
    """
    Add one batch to the session totals and save one metrics row.
    Returns (total_records, total_tokens) for the session.

    trap_metrics row meaning:
      records_served / tokens_served = amount in THIS interval
      context_size                   = running total of tokens so far
                                       (what a client that keeps everything
                                       in its context window has to hold)
      response_time_ms               = how long this interval took
    """
    db.query(TrapSession).filter(TrapSession.id == session_id).update(
        {
            TrapSession.records_served: TrapSession.records_served + records,
            TrapSession.bytes_served: TrapSession.bytes_served + size_bytes,
            TrapSession.tokens_served: TrapSession.tokens_served + tokens,
        }
    )

    session = db.query(TrapSession).filter(TrapSession.id == session_id).one()

    if records > 0:
        db.add(
            TrapMetric(
                trap_session_id=session_id,
                records_served=records,
                tokens_served=tokens,
                context_size=session.tokens_served,
                response_time_ms=response_ms,
                run_id=session.run_id,
            )
        )

    db.commit()

    ws_manager.broadcast_sync(
        "trap_event",
        {
            "action": "progress",
            "session_id": session_id,
            "status": session.status,
            "records_served": session.records_served,
            "tokens_served": session.tokens_served,
            "records_added": records,
            "tokens_added": tokens,
        },
    )

    return session.records_served, session.tokens_served


def refusal_reply(retry_after: int) -> TrapReply:
    # Deliberately generic: it must not reveal that a trap exists.
    return TrapReply(
        status=429,
        body={"detail": "Too many requests. Please slow down."},
        headers={"Retry-After": str(max(retry_after, 1))},
    )


def reset_all():
    """Admin/test helper: close open sessions and forget cooldowns."""
    global _cooldown_floor

    _sticky.clear()
    _cooldown_floor = utcnow()
    expire_all_open_sessions()


# ---------------------------------------------------------
# answering redirected requests (list / item / search)
# ---------------------------------------------------------

def serve_redirected(ip: str, plan: dict) -> TrapReply:
    started = time.perf_counter()
    db = SecuritySessionLocal()

    try:
        session, refusal = open_or_continue_session(db, ip)

        if refusal is not None:
            return refusal_reply(refusal)

        served_before = session.records_served
        remaining = cfg.MAX_TRAP_RECORDS - served_before

        if remaining <= 0:
            finish_session(db, session.id, "COMPLETED")
            return refusal_reply(cfg.TRAP_COOLDOWN_SECONDS)

        kind = plan["kind"]

        if kind == "item":
            ids = [plan["item_id"]]
        elif kind == "list":
            ids = synthetic.page_ids(plan["page"], plan["size"])
        elif kind == "salary":
            ids = synthetic.page_ids(plan.get("page", 1), plan.get("size", 20))
        else:
            ids = synthetic.search_ids(plan["query"], plan["page"], plan["size"])

        records = []
        total_bytes = 0

        if kind == "salary":
            for record_id in ids[:remaining]:
                emp = synthetic.make_record(record_id)
                sal = {
                    "salary_id": record_id,
                    "employee_id": emp["id"],
                    "employee_code": emp["employee_id"],
                    "employee_name": f"{emp['first_name']} {emp['last_name']}",
                    "email": emp["email"],
                    "basic_salary": 45000.0 + (record_id * 100 % 25000),
                    "allowances": 5000.0,
                    "deductions": 2000.0,
                    "net_salary": 48000.0 + (record_id * 100 % 25000),
                }
                size = len(json.dumps(sal).encode())
                if total_bytes + size > cfg.MAX_RESPONSE_SIZE:
                    break
                records.append(sal)
                total_bytes += size
        else:
            for record_id in ids[:remaining]:
                record = synthetic.make_record(record_id)
                size = synthetic.record_size(record)

                if total_bytes + size > cfg.MAX_RESPONSE_SIZE:
                    break

                records.append(record)
                total_bytes += size

        if not records:
            # MAX_RESPONSE_SIZE is smaller than a single record (config error)
            return refusal_reply(30)

        payload = records[0] if kind == "item" else records

        # count exactly what is sent (compact JSON, like JSONResponse)
        body_text = json.dumps(payload, separators=(",", ":"))
        body_bytes = len(body_text.encode())
        tokens = token_service.count_tokens(body_text)

        total_records, _total_tokens = add_progress(
            db,
            session.id,
            len(records),
            body_bytes,
            tokens,
            response_ms=round((time.perf_counter() - started) * 1000, 2),
        )

        # Requirement 4: Store fake logs and records in newly generated files
        log_fake_trap_data(
            session_id=session.id,
            ip=ip,
            endpoint=f"/employees ({kind})" if kind != "salary" else "/salary",
            records=records,
            tokens=tokens,
        )

        if total_records >= cfg.MAX_TRAP_RECORDS:
            finish_session(db, session.id, "COMPLETED")

        if kind == "item":
            return TrapReply(200, payload)

        return TrapReply(
            200, payload,
            {"X-Total-Count": str(cfg.TRAP_ADVERTISED_TOTAL)},
        )
    finally:
        db.close()
