"""
Attacker Simulator Configuration (Phase 10).

All simulator parameters are defined here: target URLs, safety guards,
credentials, token budgets, caps, and simulation behaviors.

Hardcoded safety guard:
Only 127.0.0.1, 127.0.0.2, and localhost are permitted as targets.
"""

from pathlib import Path

# =========================================================
# Safety Guard & Targets
# =========================================================
# The simulator will strictly refuse to execute against any host
# outside this tuple. This ensures the simulator can NEVER be pointed
# at external or unauthorized targets.
ALLOWED_HOSTS = ("127.0.0.1", "127.0.0.2", "localhost")

DEFAULT_TARGET_URL = "http://127.0.0.1:8000"

# =========================================================
# Attacker Credentials
# =========================================================
# Simulating an attacker holding stolen credentials for the HR role.
AUTH_USERNAME = "hr"
AUTH_PASSWORD = "HR@123"
LOGIN_ENDPOINT = "/auth/login"

# =========================================================
# Agent Context Window & Resource Limits (Stopping Conditions)
# =========================================================
# Simulates an AI scraping agent with a bounded context budget.
# The simulator halts immediately upon hitting the FIRST of these:
TOKEN_BUDGET = 50_000                  # Max context tokens before stopping
MAX_REQUESTS = 200                     # Max requests per session
MAX_SESSION_TIME_SECONDS = 120.0       # Max wall-clock run time (2 minutes)

# =========================================================
# Token Counting
# =========================================================
TOKEN_COUNTER = "tiktoken"             # "tiktoken" with cl100k_base or "estimate"
TOKEN_ENCODING = "cl100k_base"

# =========================================================
# Detection & Trap Signatures
# =========================================================
DECOY_ENDPOINT = "/api/trap/records"
TRAP_EMAIL_DOMAIN = "corp-example.com"
IP_BLOCK_DETAIL_KEYWORD = "temporarily blocked"

# =========================================================
# Reconnaissance Parameters
# =========================================================
# Probing endpoints to discover system structure
PROBE_ENDPOINTS = [
    "/departments/",
    "/salary/",
    "/users/",                          # Admin-only: triggers 403 (role-based, NOT block)
    "/attendance-page",
    "/payroll-page",
    "/api/trap/records",               # Decoy legacy export
]

# Common employee search queries
SEARCH_QUERIES = [
    "john", "priya", "kumar", "singh", "sharma",
    "manager", "engineer", "admin", "analyst", "lead",
    "developer", "specialist", "sales", "finance", "hr"
]

# Request pacing delay (seconds) between individual requests
REQUEST_DELAY_SECONDS = 0.05

# =========================================================
# Output & Reports
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"

