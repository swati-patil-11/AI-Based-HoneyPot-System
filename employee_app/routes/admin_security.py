import ipaddress
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config as cfg
from dependencies import require_roles
from sqlalchemy import func

from models.security import BlockedIP, RequestLog, TrapMetric, TrapSession
from security_database import SecuritySessionLocal, get_security_db, utcnow
from services import detection_service, experiment_service, system_metrics_service, token_service, trap_service
from services.blocking_service import create_block, unblock
from services.ws_manager import manager as ws_manager


router = APIRouter(
    prefix="/admin/security",
    tags=["Admin Security"]
)


class BlockCreate(BaseModel):
    ip_address: str
    minutes: int = 5
    reason: str = "Manual block by admin"


class ExperimentStartRequest(BaseModel):
    name: str
    trap_enabled: bool = False
    config_snapshot: dict | None = None


class ExperimentFinishRequest(BaseModel):
    simulator_report: dict | None = None


class TrapToggleRequest(BaseModel):
    enabled: bool



def _block_to_dict(block: BlockedIP) -> dict:
    remaining = 0

    if block.status == "ACTIVE" and block.expires_at:
        remaining = max(0, int((block.expires_at - utcnow()).total_seconds()))

    return {
        "id": block.id,
        "ip_address": block.ip_address,
        "status": block.status,
        "reason": block.reason,
        "created_at": (block.created_at.isoformat() + "Z") if block.created_at else None,
        "expires_at": (block.expires_at.isoformat() + "Z") if block.expires_at else None,
        "seconds_remaining": remaining,
        "created_by": block.created_by,
        "violation_count": block.violation_count,
        "trap_session_id": block.trap_session_id,
    }


@router.get("/logs")
def get_logs(
    limit: int = Query(50, ge=1, le=500),
    ip: str | None = None,
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    query = db.query(RequestLog)

    if ip:
        query = query.filter(RequestLog.ip_address == ip)

    logs = query.order_by(RequestLog.id.desc()).limit(limit).all()

    return [
        {
            "id": log.id,
            "timestamp": (log.timestamp.isoformat() + "Z") if log.timestamp else None,
            "suspicion_score": log.suspicion_score,
            "ip_address": log.ip_address,
            "method": log.method,
            "endpoint": log.endpoint,
            "query_string": log.query_string,
            "status_code": log.status_code,
            "response_time_ms": log.response_time_ms,
            "user_id": log.user_id,
            "user_agent": log.user_agent,
        }
        for log in logs
    ]


@router.get("/blocks")
def list_blocks(
    status: str | None = Query(None, description="ACTIVE, EXPIRED or UNBLOCKED"),
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    query = db.query(BlockedIP)

    if status:
        query = query.filter(BlockedIP.status == status.upper())

    blocks = query.order_by(BlockedIP.id.desc()).limit(100).all()

    return [_block_to_dict(block) for block in blocks]


@router.post("/blocks")
def block_ip(
    data: BlockCreate,
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    try:
        ipaddress.ip_address(data.ip_address)
    except ValueError:
        raise HTTPException(status_code=422, detail="Not a valid IP address")

    if not 1 <= data.minutes <= 1440:
        raise HTTPException(
            status_code=422,
            detail="minutes must be between 1 and 1440 (no permanent blocks)"
        )

    block = create_block(
        db,
        ip_address=data.ip_address,
        minutes=data.minutes,
        reason=data.reason,
        created_by=current_user.username,
    )

    return _block_to_dict(block)


@router.post("/blocks/{block_id}/unblock")
def unblock_ip(
    block_id: int,
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    block = unblock(db, block_id, current_user.username)

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    return _block_to_dict(block)


@router.get("/scores")
def get_scores(current_user=Depends(require_roles("admin"))):
    """Live suspicion score of every IP seen in the last window."""
    return [
        {
            "ip_address": ip,
            "score": result.score,
            "level": result.level,
            "points_per_signal": result.breakdown,
            "measured_values": result.metrics,
        }
        for ip, result in sorted(
            detection_service.all_snapshots().items(),
            key=lambda item: item[1].score,
            reverse=True,
        )
    ]


@router.post("/scores/reset")
def reset_scores(
    ip: str | None = None,
    current_user=Depends(require_roles("admin"))
):
    """Forget the behavior history of one IP (or all IPs)."""
    detection_service.reset(ip)
    return {"message": "Detection history cleared", "ip": ip or "all"}


@router.get("/trap-sessions")
def list_trap_sessions(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    sessions = db.query(TrapSession).order_by(TrapSession.id.desc()).limit(limit).all()

    return [
        {
            "id": s.id,
            "ip_address": s.ip_address,
            "status": s.status,
            "started_at": (s.started_at.isoformat() + "Z") if s.started_at else None,
            "ended_at": (s.ended_at.isoformat() + "Z") if s.ended_at else None,
            "records_served": s.records_served,
            "tokens_served": s.tokens_served,
            "bytes_served": s.bytes_served,
        }
        for s in sessions
    ]


@router.post("/trap/reset")
def reset_trap(current_user=Depends(require_roles("admin"))):
    """Close open trap sessions and forget cooldowns (between experiments)."""
    trap_service.reset_all()
    return {"message": "Trap sessions closed and cooldowns cleared"}


@router.get("/trap-metrics")
def get_trap_metrics(
    session_id: int | None = None,
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    """
    Time series for graphs. Without session_id: the newest rows of all sessions.
    records_served / tokens_served are per interval; context_size is the
    running token total of the session.
    """
    query = db.query(TrapMetric)

    if session_id is not None:
        query = query.filter(TrapMetric.trap_session_id == session_id)

    rows = query.order_by(TrapMetric.id.desc()).limit(limit).all()
    rows.reverse()

    return [
        {
            "id": m.id,
            "trap_session_id": m.trap_session_id,
            "timestamp": m.timestamp,
            "records_served": m.records_served,
            "tokens_served": m.tokens_served,
            "context_size": m.context_size,
            "response_time_ms": m.response_time_ms,
        }
        for m in rows
    ]


@router.get("/trap-summary")
def get_trap_summary(
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin"))
):
    """One-glance numbers for the dashboard and the report."""
    totals = db.query(
        func.count(TrapSession.id),
        func.coalesce(func.sum(TrapSession.records_served), 0),
        func.coalesce(func.sum(TrapSession.tokens_served), 0),
        func.coalesce(func.sum(TrapSession.bytes_served), 0),
        func.coalesce(func.max(TrapSession.tokens_served), 0),
    ).one()

    by_status = dict(
        db.query(TrapSession.status, func.count(TrapSession.id))
        .group_by(TrapSession.status)
        .all()
    )

    sessions = totals[0]

    return {
        "token_counter": token_service.method(),
        "total_sessions": sessions,
        "sessions_by_status": by_status,
        "active_traps": by_status.get("TRAPPED", 0),
        "total_records_served": int(totals[1]),
        "total_tokens_served": int(totals[2]),
        "total_bytes_served": int(totals[3]),
        "avg_tokens_per_session": round(totals[2] / sessions, 1) if sessions else 0,
        "max_tokens_in_one_session": int(totals[4]),
    }


# =========================================================
# Experiments: Baseline vs Trap (Phase 13)
# =========================================================

@router.post("/experiments/start")
def start_experiment_endpoint(
    data: ExperimentStartRequest,
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin")),
):
    """Starts a new formal experiment run."""
    run = experiment_service.start_experiment(
        name=data.name,
        trap_enabled=data.trap_enabled,
        config_snapshot=data.config_snapshot,
        db=db,
    )
    return experiment_service._run_to_dict(run)


@router.post("/experiments/{run_id}/finish")
def finish_experiment_endpoint(
    run_id: int,
    data: ExperimentFinishRequest,
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin")),
):
    """Finishes an experiment run, tallies metrics and server resource impact."""
    run = experiment_service.finish_experiment(
        run_id=run_id,
        sim_report=data.simulator_report,
        db=db,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    return experiment_service._run_to_dict(run)


@router.get("/experiments")
def list_experiments_endpoint(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin")),
):
    """Lists completed and active experiment runs."""
    return experiment_service.list_experiments(db, limit=limit)


@router.get("/experiments/compare")
def compare_experiments_endpoint(
    baseline_id: int = Query(..., description="Run ID of the Baseline experiment (trap OFF)"),
    treatment_id: int = Query(..., description="Run ID of the Treatment experiment (trap ON)"),
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin")),
):
    """Computes a side-by-side comparative analysis between Baseline and Treatment runs."""
    try:
        return experiment_service.compare_runs(baseline_id, treatment_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/experiments/set-trap")
def set_trap_toggle_endpoint(
    data: TrapToggleRequest,
    current_user=Depends(require_roles("admin")),
):
    """Dynamically toggles TRAP_ENABLED without needing to restart the server."""
    cfg.set_trap_enabled(data.enabled)
    return {"message": f"TRAP_ENABLED set to {cfg.TRAP_ENABLED}", "trap_enabled": cfg.TRAP_ENABLED}



# =========================================================
# System Metrics & WebSocket (Phase 11)
# =========================================================

@router.get("/system-metrics")
def get_system_metrics(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_security_db),
    current_user=Depends(require_roles("admin")),
):
    """Retrieve recent server CPU, memory, RPS, and active trap snapshots."""
    return system_metrics_service.get_recent_metrics(db, limit=limit)


def verify_admin_token(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
        if payload.get("role") == "admin":
            return payload
    except Exception:
        pass
    return None


@router.websocket("/ws")
async def admin_ws_route(websocket: WebSocket, token: str | None = None):
    await handle_admin_ws(websocket, token)


async def handle_admin_ws(websocket: WebSocket, token: str | None = None):
    user_payload = verify_admin_token(token)
    if not user_payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(websocket)

    # Initial state push
    try:
        db = SecuritySessionLocal()
        try:
            active_blocks = db.query(BlockedIP).filter(BlockedIP.status == "ACTIVE").all()
            blocks_data = [_block_to_dict(b) for b in active_blocks]
            recent_metrics = system_metrics_service.get_recent_metrics(db, limit=20)
        finally:
            db.close()

        init_data = {
            "scores": [
                {
                    "ip_address": ip,
                    "score": result.score,
                    "level": result.level,
                    "points_per_signal": result.breakdown,
                }
                for ip, result in sorted(
                    detection_service.all_snapshots().items(),
                    key=lambda item: item[1].score,
                    reverse=True,
                )
            ],
            "active_blocks": blocks_data,
            "recent_metrics": recent_metrics,
        }
        await websocket.send_text(json.dumps({"event": "init", "data": init_data}))

        while True:
            text = await websocket.receive_text()
            if text == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[admin_ws] Client error: {e}")
    finally:
        await ws_manager.disconnect(websocket)

