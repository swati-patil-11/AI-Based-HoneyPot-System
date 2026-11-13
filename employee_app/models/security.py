from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
)

from security_database import SecurityBase, utcnow


class ExperimentRun(SecurityBase):
    """One experiment run, e.g. 'baseline' (trap off) or 'trap' (trap on)."""
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    mode = Column(String(20), nullable=False)          # baseline | trap
    trap_enabled = Column(Boolean, default=False, nullable=False)
    config_json = Column(Text, nullable=True)          # settings snapshot
    started_at = Column(DateTime, default=utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    # Experiment outcome metrics (Phase 13)
    total_requests = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    real_records_served = Column(Integer, default=0, nullable=False)
    fake_records_served = Column(Integer, default=0, nullable=False)
    time_to_first_block_sec = Column(Float, nullable=True)
    peak_cpu_percent = Column(Float, nullable=True)
    peak_memory_percent = Column(Float, nullable=True)
    avg_cpu_percent = Column(Float, nullable=True)
    avg_memory_percent = Column(Float, nullable=True)
    stop_reason = Column(String(50), nullable=True)
    simulator_report_json = Column(Text, nullable=True)


class RequestLog(SecurityBase):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    endpoint = Column(String(255), nullable=False)
    query_string = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    user_agent = Column(String(255), nullable=True)
    user_id = Column(Integer, nullable=True)           # from JWT, if present
    suspicion_score = Column(Integer, nullable=True)   # filled in Phase 6
    is_trap = Column(Boolean, default=False, nullable=False)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)


class TrapSession(SecurityBase):
    __tablename__ = "trap_sessions"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    status = Column(String(20), default="TRAPPED", nullable=False)
    # TRAPPED | COMPLETED | EXPIRED
    started_at = Column(DateTime, default=utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    records_served = Column(Integer, default=0, nullable=False)
    tokens_served = Column(Integer, default=0, nullable=False)
    bytes_served = Column(Integer, default=0, nullable=False)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)


class TrapMetric(SecurityBase):
    """Per-interval snapshot used for the experiment graphs."""
    __tablename__ = "trap_metrics"

    id = Column(Integer, primary_key=True, index=True)
    trap_session_id = Column(
        Integer, ForeignKey("trap_sessions.id"), nullable=False, index=True
    )
    timestamp = Column(DateTime, default=utcnow, nullable=False)
    records_served = Column(Integer, default=0, nullable=False)
    tokens_served = Column(Integer, default=0, nullable=False)
    context_size = Column(Integer, default=0, nullable=False)
    response_time_ms = Column(Float, nullable=True)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)


class BlockedIP(SecurityBase):
    __tablename__ = "blocked_ips"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    status = Column(String(20), default="ACTIVE", nullable=False, index=True)
    # ACTIVE | EXPIRED | UNBLOCKED
    created_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_by = Column(String(50), default="system", nullable=False)
    violation_count = Column(Integer, default=1, nullable=False)
    trap_session_id = Column(
        Integer, ForeignKey("trap_sessions.id"), nullable=True
    )


class SystemMetric(SecurityBase):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    requests_per_second = Column(Float, nullable=True)
    active_traps = Column(Integer, default=0, nullable=False)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=True)
