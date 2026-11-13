import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Copy .env.example to .env and set a value."
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# Detection engine settings (Phase 6)
# =========================================================
# Nothing about scoring is hardcoded in the code. Change a number here
# and every experiment run uses it. A snapshot of these values is saved
# with each experiment run so results can be reproduced.
#
# Each signal adds points from 0 up to its "weight".
# The points grow in a straight line until the signal reaches "full_at".
# Example: request_rate with full_at=60 and weight=20
#   30 requests in the window -> 10 points, 60 or more -> 20 points.
# The weights add up to 100, so the score is a number from 0 to 100.

DETECTION_WINDOW_SECONDS = 60          # sliding window per source IP
DETECTION_MAX_EVENTS_PER_IP = 5000     # memory safety cap

DETECTION_SIGNALS = {
    "request_rate":         {"full_at": 60, "weight": 20},  # requests per minute
    "sequential_ids":       {"full_at": 10, "weight": 20},  # /employees/1, /2, /3 ...
    "pagination_depth":     {"full_at": 10, "weight": 15},  # deepest page number
    "repeated_searches":    {"full_at": 10, "weight": 10},  # requests with a search term
    "auth_failures":        {"full_at": 5,  "weight": 15},  # 401 responses
    "distinct_endpoints":   {"full_at": 8,  "weight": 10},  # different endpoints touched
    "automated_user_agent": {"full_at": 1,  "weight": 5},   # curl, python, httpx ...
    "short_intervals":      {"full_at": 10, "weight": 5},   # many very fast gaps
}

SHORT_INTERVAL_SECONDS = 0.3           # a gap below this counts as "very short"

# Score levels (lowest score of each level)
LEVEL_MONITOR = 31
LEVEL_SUSPICIOUS = 61
TRAP_THRESHOLD = int(os.getenv("TRAP_THRESHOLD", "75"))                    # score >= this means "trap level"

AUTOMATED_UA_KEYWORDS = (
    "python", "httpx", "requests", "aiohttp", "curl", "wget", "scrapy",
    "go-http-client", "okhttp", "libwww", "java/", "bot", "spider", "crawler",
)

SEARCH_PARAMS = ("q", "search", "query", "keyword", "name")

# Paths the detector ignores (admin tools, docs, static files)
DETECTION_EXEMPT_PREFIXES = (
    "/static", "/admin/security", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
)


def detection_config_snapshot() -> dict:
    """All detection settings as a dict (saved with each experiment run)."""
    return {
        "window_seconds": DETECTION_WINDOW_SECONDS,
        "signals": DETECTION_SIGNALS,
        "short_interval_seconds": SHORT_INTERVAL_SECONDS,
        "levels": {
            "monitor": LEVEL_MONITOR,
            "suspicious": LEVEL_SUSPICIOUS,
            "trap": TRAP_THRESHOLD,
        },
    }


# =========================================================
# Trap settings (Phase 7)
# =========================================================
# Every limit below is enforced by the server, so the trap can never
# use unbounded memory, time or bandwidth.

# Master switch. False = "baseline" mode: no redirect, no decoy endpoint.
# Set it in .env with  TRAP_ENABLED=false  for the baseline experiment.
TRAP_ENABLED = os.getenv("TRAP_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def set_trap_enabled(enabled: bool):
    global TRAP_ENABLED
    TRAP_ENABLED = enabled


MAX_ACTIVE_TRAPS = 5                   # trap sessions open at the same time
MAX_TRAP_RECORDS = 500                 # synthetic records per trap session
MAX_TRAP_SESSION_TIME = 120            # seconds a trap session may last
MAX_RESPONSE_SIZE = 256 * 1024         # bytes per single response (256 KB)
MAX_SYNTHETIC_RECORD_RATE = 50         # records per second (streaming throttle)
TRAP_COOLDOWN_SECONDS = int(os.getenv("TRAP_COOLDOWN_SECONDS", "5"))            # after a session ends, no new one for this long (5s in lab)

TRAP_SEED = 20260101                   # same seed -> same fake data every run
TRAP_EMAIL_DOMAIN = "corp-example.com" # marks synthetic records for YOUR analysis
TRAP_ADVERTISED_TOTAL = 50000          # fake "X-Total-Count" shown to the attacker


def trap_config_snapshot() -> dict:
    return {
        "trap_enabled": TRAP_ENABLED,
        "max_active_traps": MAX_ACTIVE_TRAPS,
        "max_trap_records": MAX_TRAP_RECORDS,
        "max_trap_session_time": MAX_TRAP_SESSION_TIME,
        "max_response_size": MAX_RESPONSE_SIZE,
        "max_synthetic_record_rate": MAX_SYNTHETIC_RECORD_RATE,
        "trap_cooldown_seconds": TRAP_COOLDOWN_SECONDS,
        "trap_seed": TRAP_SEED,
    }


# =========================================================
# Token counting and trap metrics (Phase 8)
# =========================================================
# "tiktoken"  -> count tokens with the tiktoken library (needs internet ONCE
#                to download the encoding file, then it is cached)
# "estimate"  -> no download; tokens = characters / 4 (rough)
# If tiktoken cannot load, the server falls back to the estimate by itself.
TOKEN_COUNTER = os.getenv("TOKEN_COUNTER", "tiktoken").strip().lower()

# cl100k_base is a common proxy for an LLM tokenizer. Real models differ,
# so token counts here are an APPROXIMATION of "context used".
TOKEN_ENCODING = os.getenv("TOKEN_ENCODING", "cl100k_base")

# While streaming, save one metrics row every N records
METRIC_SNAPSHOT_EVERY_RECORDS = 50


# =========================================================
# Automatic temporary blocking (Phase 9)
# =========================================================
# A source is blocked when it KEEPS asking after the trap has run out:
# every time the trap answers "429 too many requests" to the same IP, that
# counts as one continued request. There is NO permanent ban.

# Master switch (set BLOCKING_ENABLED=false in .env to test the trap alone)
BLOCKING_ENABLED = os.getenv("BLOCKING_ENABLED", "true").strip().lower() in ("1", "true", "yes")

BLOCK_AFTER_TRAP_REQUESTS = 10         # more than this many refusals -> block
BLOCK_COUNT_WINDOW_SECONDS = 300       # refusals are counted inside this window

# 1st violation -> 5 min, 2nd -> 30 min, 3rd and later -> 120 min.
# Edit the numbers to change the escalation. Every value is temporary.
BLOCK_DURATIONS_MINUTES = (5, 30, 120)

# Violations older than this are forgotten (a clean source starts at step 1)
VIOLATION_MEMORY_HOURS = 24

# IPs that must never be blocked automatically (example: ("127.0.0.1",))
BLOCK_ALLOWLIST = ()

# Background job that marks finished blocks as EXPIRED
BLOCK_CLEANUP_INTERVAL_SECONDS = 30


def blocking_config_snapshot() -> dict:
    return {
        "blocking_enabled": BLOCKING_ENABLED,
        "block_after_trap_requests": BLOCK_AFTER_TRAP_REQUESTS,
        "block_count_window_seconds": BLOCK_COUNT_WINDOW_SECONDS,
        "block_durations_minutes": list(BLOCK_DURATIONS_MINUTES),
        "violation_memory_hours": VIOLATION_MEMORY_HOURS,
    }


# =========================================================
# System monitoring and WebSockets (Phase 11)
# =========================================================
SYSTEM_METRICS_ENABLED = os.getenv("SYSTEM_METRICS_ENABLED", "true").strip().lower() in ("1", "true", "yes")
SYSTEM_METRICS_INTERVAL_SECONDS = int(os.getenv("SYSTEM_METRICS_INTERVAL_SECONDS", "3"))


def system_metrics_config_snapshot() -> dict:
    return {
        "system_metrics_enabled": SYSTEM_METRICS_ENABLED,
        "system_metrics_interval_seconds": SYSTEM_METRICS_INTERVAL_SECONDS,
    }

