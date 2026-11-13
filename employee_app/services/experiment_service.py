"""
Experiment Tracking & Benchmarking Service (Phase 13).

Manages scientific comparison experiments (Baseline vs. Trap Treatment):
- Coordinates experiment run lifecycle (start, telemetry tagging, finish).
- Records tokens consumed, real vs fake records obtained, time-to-block, and peak CPU/RAM.
- Computes defense effectiveness metrics and side-by-side comparison matrices.
"""

from datetime import datetime
import json
from typing import Any

from sqlalchemy.orm import Session

import config as cfg
from models.security import BlockedIP, ExperimentRun, RequestLog, SystemMetric, TrapSession
from security_database import SecuritySessionLocal, utcnow
from services import system_metrics_service, trap_service


def _run_to_dict(run: ExperimentRun) -> dict[str, Any]:
    duration = None
    if run.ended_at and run.started_at:
        duration = round((run.ended_at - run.started_at).total_seconds(), 2)

    return {
        "id": run.id,
        "name": run.name,
        "mode": run.mode,
        "trap_enabled": bool(run.trap_enabled),
        "started_at": run.started_at.isoformat() + "Z" if run.started_at else None,
        "ended_at": run.ended_at.isoformat() + "Z" if run.ended_at else None,
        "duration_seconds": duration,
        "total_requests": run.total_requests or 0,
        "total_tokens": run.total_tokens or 0,
        "real_records_served": run.real_records_served or 0,
        "fake_records_served": run.fake_records_served or 0,
        "time_to_first_block_sec": run.time_to_first_block_sec,
        "peak_cpu_percent": run.peak_cpu_percent,
        "peak_memory_percent": run.peak_memory_percent,
        "avg_cpu_percent": run.avg_cpu_percent,
        "avg_memory_percent": run.avg_memory_percent,
        "stop_reason": run.stop_reason,
    }


def start_experiment(
    name: str,
    trap_enabled: bool,
    config_snapshot: dict | None = None,
    db: Session | None = None,
) -> ExperimentRun:
    """Begins a new experiment run and tags server telemetry."""
    should_close = False
    if db is None:
        db = SecuritySessionLocal()
        should_close = True

    try:
        mode = "trap" if trap_enabled else "baseline"
        cfg_dump = json.dumps(config_snapshot or {
            "trap": cfg.trap_config_snapshot(),
            "detection": cfg.detection_config_snapshot(),
            "blocking": cfg.blocking_config_snapshot(),
        })

        run = ExperimentRun(
            name=name,
            mode=mode,
            trap_enabled=trap_enabled,
            config_json=cfg_dump,
            started_at=utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Notify telemetry to associate metrics with this run
        system_metrics_service.set_active_run_id(run.id)
        return run
    finally:
        if should_close:
            db.close()


def finish_experiment(
    run_id: int,
    sim_report: dict | None = None,
    db: Session | None = None,
) -> ExperimentRun | None:
    """Concludes an experiment run, tallies metrics and server resource impact."""
    should_close = False
    if db is None:
        db = SecuritySessionLocal()
        should_close = True

    try:
        run = db.get(ExperimentRun, run_id)
        if not run:
            return None

        run.ended_at = utcnow()
        system_metrics_service.set_active_run_id(None)

        # 1. Simulator report metrics
        if sim_report:
            summary = sim_report.get("summary", {})
            run.total_requests = summary.get("total_requests", 0)
            run.total_tokens = summary.get("total_tokens_consumed", 0)
            run.real_records_served = summary.get("real_records_obtained", 0)
            run.fake_records_served = summary.get("fake_records_obtained", 0)
            run.stop_reason = sim_report.get("stop_reason")
            run.simulator_report_json = json.dumps(sim_report)

        # 2. Server-side system telemetry for this window
        metrics = (
            db.query(SystemMetric)
            .filter(SystemMetric.run_id == run.id)
            .all()
        )
        if metrics:
            cpus = [m.cpu_percent for m in metrics if m.cpu_percent is not None]
            mems = [m.memory_percent for m in metrics if m.memory_percent is not None]
            if cpus:
                run.peak_cpu_percent = round(max(cpus), 2)
                run.avg_cpu_percent = round(sum(cpus) / len(cpus), 2)
            if mems:
                run.peak_memory_percent = round(max(mems), 2)
                run.avg_memory_percent = round(sum(mems) / len(mems), 2)

        # 3. Check for blocks triggered during this run
        first_block = (
            db.query(BlockedIP)
            .filter(
                BlockedIP.created_at >= run.started_at,
                BlockedIP.created_at <= run.ended_at,
            )
            .order_by(BlockedIP.id.asc())
            .first()
        )
        if first_block and first_block.created_at:
            delta = (first_block.created_at - run.started_at).total_seconds()
            run.time_to_first_block_sec = round(max(0.0, delta), 2)

        db.commit()
        db.refresh(run)
        return run
    finally:
        if should_close:
            db.close()


def list_experiments(db: Session, limit: int = 50) -> list[dict]:
    runs = (
        db.query(ExperimentRun)
        .order_by(ExperimentRun.id.desc())
        .limit(limit)
        .all()
    )
    return [_run_to_dict(r) for r in runs]


def compare_runs(baseline_id: int, treatment_id: int, db: Session) -> dict:
    """Computes side-by-side comparative analysis between Baseline and Treatment."""
    b_run = db.get(ExperimentRun, baseline_id)
    t_run = db.get(ExperimentRun, treatment_id)

    if not b_run or not t_run:
        raise ValueError("One or both experiment run IDs not found.")

    b_dict = _run_to_dict(b_run)
    t_dict = _run_to_dict(t_run)

    # Reduction in real records stolen
    real_b = b_dict["real_records_served"]
    real_t = t_dict["real_records_served"]
    leakage_reduction_pct = 0.0
    if real_b > 0:
        leakage_reduction_pct = round(((real_b - real_t) / real_b) * 100, 1)
    elif real_b == 0 and real_t == 0:
        leakage_reduction_pct = 100.0

    # Token waste factor (how many fake tokens vs real data)
    fake_t = t_dict["fake_records_served"]
    fake_tokens_t = t_dict["total_tokens"]

    comparison = {
        "baseline": b_dict,
        "treatment": t_dict,
        "analysis": {
            "real_records_stolen_baseline": real_b,
            "real_records_stolen_treatment": real_t,
            "real_data_protected_percent": leakage_reduction_pct,
            "fake_records_injected": fake_t,
            "tokens_consumed_baseline": b_dict["total_tokens"],
            "tokens_consumed_treatment": fake_tokens_t,
            "tokens_wasted_on_deception": fake_tokens_t if t_dict["trap_enabled"] else 0,
            "requests_to_halt_baseline": b_dict["total_requests"],
            "requests_to_halt_treatment": t_dict["total_requests"],
            "time_to_block_baseline": b_dict["time_to_first_block_sec"],
            "time_to_block_treatment": t_dict["time_to_first_block_sec"],
            "peak_cpu_delta": round((t_dict["peak_cpu_percent"] or 0) - (b_dict["peak_cpu_percent"] or 0), 2),
            "peak_memory_delta": round((t_dict["peak_memory_percent"] or 0) - (b_dict["peak_memory_percent"] or 0), 2),
        },
    }
    return comparison

