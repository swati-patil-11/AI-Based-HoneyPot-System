"""
Detection engine: turns observable behavior into a 0-100 score.

IMPORTANT: the score means "suspicious AUTOMATED behavior".
It does NOT mean "this client is an AI". Keeping those two ideas
separate is part of the research design.

How it works
    - For every source IP we keep the last N seconds of requests in memory.
    - On each new request we measure 8 behaviors from that window.
    - Each behavior adds points (see DETECTION_SIGNALS in config.py).
    - score = min(100, sum of points). Old requests drop out of the
      window, so the score falls again when the client calms down.

State is kept in memory, so run ONE server process (uvicorn default).
"""

import re
import time
from collections import deque
from dataclasses import dataclass, field

from config import (
    AUTOMATED_UA_KEYWORDS,
    DETECTION_MAX_EVENTS_PER_IP,
    DETECTION_SIGNALS,
    DETECTION_WINDOW_SECONDS,
    LEVEL_MONITOR,
    LEVEL_SUSPICIOUS,
    SEARCH_PARAMS,
    SHORT_INTERVAL_SECONDS,
    TRAP_THRESHOLD,
)


NUMERIC_ID_PATH = re.compile(r"^(.*)/(\d+)/?$")
NUMBER_SEGMENT = re.compile(r"/\d+")


@dataclass
class Event:
    t: float                 # time (monotonic seconds)
    method: str
    endpoint: str            # path with numbers replaced, e.g. /employees/{id}
    prefix: str | None       # e.g. /employees   (only when path ends in a number)
    item_id: int | None      # e.g. 17
    page: int | None         # page number, if the request is paginated
    has_search: bool


@dataclass
class IPState:
    events: deque = field(default_factory=lambda: deque(maxlen=DETECTION_MAX_EVENTS_PER_IP))
    auth_failures: deque = field(default_factory=deque)
    automated_ua: bool = False
    last_seen: float = 0.0


@dataclass
class ScoreResult:
    score: int
    level: str
    breakdown: dict          # points per signal
    metrics: dict            # raw measured values


_states: dict[str, IPState] = {}
_calls = 0


# ---------------------------------------------------------
# helpers
# ---------------------------------------------------------

def level_for(score: int) -> str:
    if score >= TRAP_THRESHOLD:
        return "TRAP"
    if score >= LEVEL_SUSPICIOUS:
        return "SUSPICIOUS"
    if score >= LEVEL_MONITOR:
        return "MONITOR"
    return "NORMAL"


def is_automated_user_agent(user_agent: str | None) -> bool:
    if not user_agent:
        return True                      # real browsers always send one

    text = user_agent.lower()

    return any(word in text for word in AUTOMATED_UA_KEYWORDS)


def _to_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_from_query(params: dict) -> int | None:
    page = _to_int(params.get("page"))

    if page is not None and page >= 1:
        return page

    offset = _to_int(params.get("skip"))

    if offset is None:
        offset = _to_int(params.get("offset"))

    if offset is not None and offset >= 0:
        size = _to_int(params.get("size")) or _to_int(params.get("limit")) or 20
        return offset // max(size, 1) + 1

    return None


def _build_event(method: str, path: str, params: dict, now: float) -> Event:
    match = NUMERIC_ID_PATH.match(path)

    return Event(
        t=now,
        method=method.upper(),
        endpoint=NUMBER_SEGMENT.sub("/{id}", path),
        prefix=match.group(1) if match else None,
        item_id=int(match.group(2)) if match else None,
        page=_page_from_query(params),
        has_search=any(params.get(name) for name in SEARCH_PARAMS),
    )


def _prune(state: IPState, now: float):
    cutoff = now - DETECTION_WINDOW_SECONDS

    while state.events and state.events[0].t < cutoff:
        state.events.popleft()

    while state.auth_failures and state.auth_failures[0] < cutoff:
        state.auth_failures.popleft()


def _longest_sequential_run(events) -> int:
    """Longest chain of GETs where the id goes up (or down) by exactly 1."""
    best = 0
    run = 0
    previous = None
    direction = 0

    for event in events:
        if event.method != "GET" or event.item_id is None:
            continue

        if previous is not None and previous.prefix == event.prefix:
            step = event.item_id - previous.item_id

            if step in (1, -1) and (direction in (0, step)):
                run += 1
                direction = step
            elif step in (1, -1):
                run = 2
                direction = step
            else:
                run = 1
                direction = 0
        else:
            run = 1
            direction = 0

        best = max(best, run)
        previous = event

    # one lone id lookup is normal; a "run" needs at least 2 in a row
    return best if best >= 2 else 0


def _measure(state: IPState) -> dict:
    events = list(state.events)
    scale = 60 / DETECTION_WINDOW_SECONDS

    pages = [e.page for e in events if e.page is not None]
    gaps = [b.t - a.t for a, b in zip(events, events[1:])]

    return {
        "request_rate": round(len(events) * scale),
        "sequential_ids": _longest_sequential_run(events),
        "pagination_depth": max(pages) if pages else 0,
        "repeated_searches": sum(1 for e in events if e.has_search),
        "auth_failures": len(state.auth_failures),
        "distinct_endpoints": len({e.endpoint for e in events}),
        # only counts while the IP is actually sending requests in the window
        "automated_user_agent": 1 if (state.automated_ua and events) else 0,
        "short_intervals": sum(1 for g in gaps if g < SHORT_INTERVAL_SECONDS),
    }


def _score(metrics: dict) -> ScoreResult:
    breakdown = {}

    for name, rule in DETECTION_SIGNALS.items():
        value = metrics.get(name, 0)
        share = min(value / rule["full_at"], 1.0) if rule["full_at"] else 0
        breakdown[name] = round(rule["weight"] * share, 1)

    score = min(100, round(sum(breakdown.values())))

    return ScoreResult(
        score=score,
        level=level_for(score),
        breakdown=breakdown,
        metrics=metrics,
    )


def _cleanup(now: float):
    """Forget IPs that have been quiet for longer than the window."""
    for ip in list(_states):
        state = _states[ip]
        _prune(state, now)

        if not state.events and not state.auth_failures:
            del _states[ip]


# ---------------------------------------------------------
# public API
# ---------------------------------------------------------

def record_request(
    ip: str,
    method: str,
    path: str,
    params: dict,
    user_agent: str | None,
    now: float | None = None,
) -> ScoreResult:
    """Record one request from this IP and return its current score."""
    global _calls

    now = time.monotonic() if now is None else now

    state = _states.setdefault(ip, IPState())
    state.last_seen = now
    state.automated_ua = is_automated_user_agent(user_agent)
    state.events.append(_build_event(method, path, params, now))

    _prune(state, now)

    _calls += 1
    if _calls % 500 == 0:
        _cleanup(now)

    return _score(_measure(state))


def record_auth_failure(ip: str, now: float | None = None):
    now = time.monotonic() if now is None else now

    state = _states.setdefault(ip, IPState())
    state.auth_failures.append(now)


def snapshot(ip: str, now: float | None = None) -> ScoreResult:
    """Current score for an IP without recording a new request."""
    now = time.monotonic() if now is None else now

    state = _states.get(ip)

    if state is None:
        return _score(_measure(IPState()))

    _prune(state, now)

    return _score(_measure(state))


def all_snapshots(now: float | None = None) -> dict:
    now = time.monotonic() if now is None else now

    return {ip: snapshot(ip, now) for ip in list(_states)}


def reset(ip: str | None = None):
    """Forget one IP, or everything (used between experiment runs)."""
    if ip is None:
        _states.clear()
    else:
        _states.pop(ip, None)
