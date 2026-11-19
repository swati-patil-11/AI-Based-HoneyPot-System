"""
Decoy endpoint: a "legacy bulk export" that looks valuable.

Nothing real is behind it. It streams synthetic records one at a time,
so server memory stays flat no matter how long the client keeps reading.
Normal app pages never link to it; it only shows up in /docs and
/openapi.json, where an automated scanner would find it.
"""

import asyncio
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

import config as cfg
from dependencies import require_roles
from models.security import TrapSession
from security_database import SecuritySessionLocal, utcnow
from services import synthetic_data_service as synthetic
from services import blocking_service, token_service, trap_service
from services.request_utils import get_client_ip


router = APIRouter(
    prefix="/api/trap",
    tags=["Legacy Export"]
)


def _open_session(ip: str):
    db = SecuritySessionLocal()

    try:
        session, refusal = trap_service.open_or_continue_session(db, ip)

        if refusal is not None:
            return None, 0, refusal

        return session.id, session.records_served, None
    finally:
        db.close()


async def _stream(session_id: int, already_served: int, ip: str = "127.0.0.1"):
    """
    One record at a time. Stops at the FIRST limit reached:
    records per session, session time, response size, or (slowed down)
    record rate. Counters are saved even if the client disconnects.
    """
    db = SecuritySessionLocal()

    sent = 0
    sent_bytes = 0
    sent_tokens = 0
    saved = 0
    saved_bytes = 0
    saved_tokens = 0
    stop_status = None
    started = time.monotonic()
    interval_started = time.perf_counter()
    streamed_records = []

    try:
        session = db.get(TrapSession, session_id)
        time_left = cfg.MAX_TRAP_SESSION_TIME - (
            utcnow() - session.started_at
        ).total_seconds()

        next_id = already_served + 1

        while True:
            if already_served + sent >= cfg.MAX_TRAP_RECORDS:
                stop_status = "COMPLETED"
                break

            if time.monotonic() - started >= time_left:
                stop_status = "EXPIRED"
                break

            rec = synthetic.make_record(next_id)
            streamed_records.append(rec)
            line = json.dumps(rec) + "\n"
            size = len(line.encode())

            if sent_bytes + size > cfg.MAX_RESPONSE_SIZE:
                break                    # this response ends; the session continues

            yield line

            sent += 1
            sent_bytes += size
            sent_tokens += token_service.count_tokens(line)
            next_id += 1

            if sent % cfg.METRIC_SNAPSHOT_EVERY_RECORDS == 0:
                trap_service.add_progress(
                    db, session_id,
                    sent - saved,
                    sent_bytes - saved_bytes,
                    sent_tokens - saved_tokens,
                    response_ms=round((time.perf_counter() - interval_started) * 1000, 2),
                )
                saved, saved_bytes, saved_tokens = sent, sent_bytes, sent_tokens
                interval_started = time.perf_counter()

            await asyncio.sleep(1 / cfg.MAX_SYNTHETIC_RECORD_RATE)

    finally:
        # runs on normal end AND when the client disconnects
        trap_service.add_progress(
            db, session_id,
            sent - saved,
            sent_bytes - saved_bytes,
            sent_tokens - saved_tokens,
            response_ms=round((time.perf_counter() - interval_started) * 1000, 2),
        )

        # Requirement 4: Save streamed fake records to new log files
        if streamed_records:
            trap_service.log_fake_trap_data(
                session_id, ip, "/api/trap/records", streamed_records, sent_tokens
            )

        if not stop_status and (sent > 0 or already_served > 0):
            stop_status = "COMPLETED"

        if stop_status:
            trap_service.finish_session(db, session_id, stop_status)

        db.close()


@router.get(
    "/records",
    summary="Bulk export of all employee records (legacy)",
)
async def export_records(
    request: Request,
    current_user=Depends(require_roles("admin", "hr"))
):
    if not cfg.TRAP_ENABLED:
        raise HTTPException(status_code=404, detail="Not Found")

    request.state.is_trap = True

    client_ip = get_client_ip(request)
    session_id, already_served, refusal = await run_in_threadpool(
        _open_session, client_ip
    )

    if refusal is not None:
        await run_in_threadpool(
            blocking_service.register_trap_refusal, client_ip
        )
        reply = trap_service.refusal_reply(refusal)
        return JSONResponse(reply.body, status_code=reply.status, headers=reply.headers)

    return StreamingResponse(
        _stream(session_id, already_served, client_ip),
        media_type="application/x-ndjson",
    )
