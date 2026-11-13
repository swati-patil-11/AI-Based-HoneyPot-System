"""
System Metrics Collector Service (Phase 11).

Samples server CPU% and memory usage on an interval (default: 2-3s) using psutil.
Stores snapshots in the system_metrics table of security.db and broadcasts
real-time metrics over the admin WebSocket.

Design considerations:
- psutil.cpu_percent(interval=None) is strictly non-blocking.
- Maintains a thread-safe request counter to compute requests per second (RPS).
- Zero meaningful overhead so monitoring does not perturb experiment benchmarks.
"""

import asyncio
import threading
import time

from fastapi.concurrency import run_in_threadpool
import psutil
from sqlalchemy.orm import Session

import config as cfg
from models.security import SystemMetric, TrapSession
from security_database import SecuritySessionLocal, utcnow
from services.ws_manager import manager as ws_manager


class _RequestCounter:
    def __init__(self):
        self._count = 0
        self._last_time = time.monotonic()
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

    def get_and_reset_rate(self) -> float:
        now = time.monotonic()
        with self._lock:
            elapsed = now - self._last_time
            count = self._count
            self._count = 0
            self._last_time = now

        if elapsed <= 0:
            return 0.0
        return round(count / elapsed, 2)


_request_counter = _RequestCounter()
_active_run_id: int | None = None


def count_request():
    """Notifies the metrics collector of an incoming request for RPS calculation."""
    _request_counter.increment()


def set_active_run_id(run_id: int | None):
    global _active_run_id
    _active_run_id = run_id


def sample_metrics(db: Session) -> dict:
    """Samples instantaneous system state and saves a row to security.db."""
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory().percent
    rps = _request_counter.get_and_reset_rate()

    active_traps = (
        db.query(TrapSession)
        .filter(TrapSession.status == "TRAPPED")
        .count()
    )

    metric = SystemMetric(
        timestamp=utcnow(),
        cpu_percent=cpu,
        memory_percent=mem,
        requests_per_second=rps,
        active_traps=active_traps,
        run_id=_active_run_id,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)

    data = {
        "id": metric.id,
        "timestamp": metric.timestamp.isoformat() + "Z",
        "cpu_percent": metric.cpu_percent,
        "memory_percent": metric.memory_percent,
        "requests_per_second": metric.requests_per_second,
        "active_traps": metric.active_traps,
        "run_id": metric.run_id,
    }

    ws_manager.broadcast_sync("system_metric", data)
    return data


def collect_once() -> dict | None:
    db = SecuritySessionLocal()
    try:
        return sample_metrics(db)
    except Exception as err:
        print(f"[system_metrics_service] Collection error: {err}")
        return None
    finally:
        db.close()


def get_recent_metrics(db: Session, limit: int = 50) -> list[dict]:
    rows = (
        db.query(SystemMetric)
        .order_by(SystemMetric.id.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {
            "id": m.id,
            "timestamp": m.timestamp.isoformat() + "Z",
            "cpu_percent": m.cpu_percent,
            "memory_percent": m.memory_percent,
            "requests_per_second": m.requests_per_second,
            "active_traps": m.active_traps,
            "run_id": m.run_id,
        }
        for m in rows
    ]


async def metrics_loop():
    """Background loop that periodically records and broadcasts server health."""
    # Warm up CPU measurement
    psutil.cpu_percent(interval=None)

    while True:
        try:
            if cfg.SYSTEM_METRICS_ENABLED:
                await run_in_threadpool(collect_once)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"[system_metrics_service] Loop error: {error}")

        await asyncio.sleep(cfg.SYSTEM_METRICS_INTERVAL_SECONDS)

