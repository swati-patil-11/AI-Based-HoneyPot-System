# AI Context-Window Exhaustion Trap for AI-Driven Reconnaissance

A defensive research prototype that detects automated reconnaissance behavior against a web application and redirects it to a bounded "trap" serving synthetic data — designed to exhaust an automated agent's limited context budget rather than simply blocking it outright.

> **Research scope.** This is an academic experiment, not a production security product and not a claim to "defeat" AI agents. It measures whether a context-exhaustion trap can reduce real-data exposure per unit of attacker effort. All testing is restricted to localhost / private networks.

---

## What this project demonstrates

1. A real, working **Employee Management System** (the protected application).
2. A **behavioral detection engine** that scores every source IP from 0–100 using 8 observable signals (request rate, sequential ID access, pagination depth, repeated searches, auth failures, endpoint breadth, automated User-Agent, short request intervals) — without ever assuming the client is or isn't an AI.
3. A **trap** that, once a source is flagged, serves Faker-generated synthetic employee data instead of real records, through the same endpoints, bounded by strict limits (records, time, response size).
4. **Token counting** (via `tiktoken`) on every trap response, modeling how much of an AI agent's context window gets consumed.
5. **Escalating temporary IP blocking** (5 → 30 → 120 minutes, never permanent) for sources that persist past the trap.
6. A **live security dashboard** (WebSocket-driven) showing CPU/memory, live suspicion scores, trap sessions, and blocks.
7. A standalone **AI attacker simulator** that models an AI reconnaissance agent with a bounded context window, used to run controlled experiments.
8. A **baseline-vs-trap experiment**, comparing attacker effectiveness with the trap disabled vs. enabled.

---

## Headline result

| Metric | Baseline (trap OFF) | Trap ON |
|---|---|---|
| Requests sent before stopping (mean of 5 trials) | 121 | 9 |
| Context tokens used | 50,054 | 68,794 |
| Real employee records read | 416 | 20 |
| Synthetic (fake) records read | 0 | 500 |

**With the trap enabled, the simulated attacker's context budget was exhausted using 92.6% fewer requests, and real-data exposure dropped by over 20×.**

---

## Architecture

```
┌─────────────────────────┐   ┌──────────────────────────────┐
│  Admin / HR browser      │   │  AI attacker simulator        │
│  (real client)           │   │  (separate process, simulated │
│                          │   │   stolen HR credentials)       │
└───────────┬──────────────┘   └───────────────┬───────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (uvicorn)                │
│  Same endpoints serve every client                            │
│                                                                │
│  Request logger → IP blocker → Detection engine                │
│                                     │                           │
│                     ┌───────────────┴───────────────┐          │
│                     ▼                               ▼          │
│            Normal traffic                   Flagged traffic    │
│            (score < 81)                      (score ≥ 81)      │
│                     │                               │           │
│                     ▼                               ▼           │
│            Real app routes                   Trap service      │
│          (CRUD, auth, search)          (Faker data, bounded)    │
└──────────┬──────────────────────────────────────────┬──────────┘
           ▼                                           ▼
  employee.db (SQLite)                    Token counter (tiktoken)
  Real employee data                              │
                                                    ▼
                                           Blocking service
                                    (escalating 5→30→120 min, auto-expire)
                                                    │
                                                    ▼
                                    security.db (SQLite)
                         Logs, trap sessions, blocked_ips, system_metrics
                                                    │
                                                    ▼
                                        Security dashboard
                                   (WebSocket push, live, admin-only)
```

Two databases are kept **physically separate**: `employee.db` (real data) and `security.db` (all security telemetry). The trap and detection code never import the `Employee` model or open `employee.db` — it is structurally impossible for them to read or leak real data.

---

## Tech stack

- **Backend:** FastAPI, SQLAlchemy, SQLite (two databases)
- **Auth:** JWT, bcrypt password hashing, role-based access (admin / hr / employee)
- **Frontend:** Server-rendered Jinja2 templates + vanilla JavaScript + Chart.js (no React/Vue)
- **Synthetic data:** Faker (seeded, reproducible)
- **Token counting:** `tiktoken` (`cl100k_base`), with a characters ÷ 4 fallback estimate
- **Live updates:** native FastAPI/Starlette WebSockets (no Socket.io)
- **Attacker simulator:** standalone Python client using `httpx` + `tiktoken`, localhost/private-IP only by code-level safety check
- **Monitoring:** `psutil` (CPU/memory)

---

## Project structure

```
AI-Based-HoneyPot-System/
├── employee_app/
│   ├── main.py
│   ├── config.py                  # detection, trap, blocking, monitoring settings
│   ├── .env                       # SECRET_KEY (not committed)
│   ├── routes/                    # auth, employees, departments, attendance,
│   │                               # salary, users, admin_security, trap
│   ├── services/                  # detection, trap, synthetic_data, token,
│   │                               # blocking, monitoring, auth
│   ├── middleware/                 # request_logger, ip_blocker, detection
│   ├── models/                     # employee models + security.py
│   ├── websocket/                  # dashboard.py (live push)
│   ├── database/                   # employee.db, security.db (not committed)
│   ├── static/                     # css, js (incl. security_dashboard.js)
│   ├── templates/                  # Jinja pages, incl. security_dashboard.html
│   ├── seed_employees.py
│   └── unblock_all.py
├── attacker_simulator/
│   ├── ai_attacker.py
│   ├── config.py
│   ├── run_experiment.py           # runs N trials for one condition
│   ├── compare_results.py          # baseline vs trap comparison + charts
│   └── reports/                    # JSON run reports + chart PNGs
└── requirements.txt
```

---

## Setup

### 1. Backend

```bash
cd employee_app
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r ../requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
python -c "import secrets; print(secrets.token_hex(32))"
# paste the printed key into .env as SECRET_KEY=...

python seed_employees.py 300   # seed synthetic employee data
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000` for the app, or `http://127.0.0.1:8000/docs` for the interactive API.

### 2. Attacker simulator

```bash
cd attacker_simulator
pip install -r requirements.txt
python ai_attacker.py
```

The simulator logs in with a test HR account (simulating stolen/leaked credentials), performs reconnaissance, and stops once it hits its context token budget, a request cap, a time cap, or gets blocked.

---

## Running the baseline-vs-trap experiment

```bash
# Terminal 1 (baseline): trap disabled
set TRAP_ENABLED=false          # PowerShell: $env:TRAP_ENABLED="false"
uvicorn main:app

# Terminal 2
python run_experiment.py --label trap_off --runs 5
```

```bash
# Terminal 1 (trap on): restart without the flag
uvicorn main:app

# Terminal 2
python run_experiment.py --label trap_on --runs 5
python compare_results.py reports/experiment_trap_off_*.json reports/experiment_trap_on_*.json
```

This prints a results table and saves comparison charts to `reports/charts/`.

---

## Key configuration values (see `config.py`)

| Setting | Value |
|---|---|
| Trap threshold | suspicion score ≥ 81 |
| Detection window | 60 seconds (sliding) |
| Max trap records / session | 500 |
| Max trap session time | 120 seconds |
| Max response size | 256 KB |
| Block escalation | 5 → 30 → 120 minutes (never permanent) |
| Block trigger | > 10 refused requests in 5 minutes |
| Violation memory | 24 hours |
| Attacker context budget (default) | 50,000 tokens |

---

## Known limitations

- The attacker simulator follows a **fixed, scripted** reconnaissance pattern, not a reasoning AI agent — results describe what this pattern achieves, not the full range of adaptive attacker behavior.
- A narrow, slow sequential-ID-only access pattern can stay **under the detection threshold** (scored ~50/100 in testing, below the 81 trap threshold).
- Token counting via `tiktoken` is an **approximation**; a real model's own tokenizer may differ.
- Detection, trapping, and blocking are keyed by **source IP**, which is weak under NAT/shared addresses.
- Detection state lives in a **single process's memory** — the design assumes one server process, not a horizontally-scaled deployment.

See the full project report for the complete discussion, including the experiment methodology and results.

---

## Ethical use

- The attacker simulator refuses (at the code level) to target anything other than `localhost` or a private IP address.
- All employee data is synthetically generated (Faker, fixed seed) — no real person's data exists anywhere in this system.
- Every automatic defensive action (IP blocking) is strictly temporary and can be lifted early by an administrator.
- This project is presented as research into one defensive technique, not a production-ready security product.

---
