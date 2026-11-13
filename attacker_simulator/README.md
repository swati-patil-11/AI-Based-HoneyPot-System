# Attacker Simulator (Phase 10)

A standalone AI reconnaissance and scraping agent simulator designed for defensive deception security experiments.

It behaves like an automated AI agent with stolen credentials, walking IDs, paging through employee records, running search queries, probing endpoints, and hitting decoy honeypot streams while tracking its own token budget (simulating context window exhaustion).

---

## Safety Guard

The simulator contains a **hardcoded safety guard** preventing execution against anything other than local lab environments:
- Allowed hosts: `127.0.0.1`, `127.0.0.2`, `localhost`
- Any attempt to target an external domain or non-local IP raises an immediate `ValueError` and terminates execution.

---

## Requirements

The simulator requires Python 3.10+ and uses:
- `httpx` (HTTP client with NDJSON streaming support; automatic fallback to `requests`/`urllib`)
- `tiktoken` (cl100k_base tokenizer; automatic fallback to `chars/4` estimation)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Quick Start

1. **Ensure the employee application is running** (default: `http://127.0.0.1:8000`).
2. **Run the simulator**:
   ```bash
   python simulator.py
   ```

---

## Attack Scenarios

Use the `--scenario` flag to select an attack pattern:

| Scenario | Description |
| :--- | :--- |
| `mixed` *(default)* | Full autonomous agent workflow: endpoint probing -> decoy stream exploitation -> pagination walking -> sequential ID walking -> keyword searches. |
| `id_walk_only` | Sequential `GET /employees/{id}` walking (demonstrates the limitation where low-rate ID walking stays below the 81 suspicion threshold). |
| `pagination_only` | Deep pagination walking `GET /employees/?page=N&size=M`. |
| `decoy_only` | Direct consumption of the decoy legacy export stream `GET /api/trap/records`. |
| `search_only` | Repeated search queries `GET /employees/search?q=...`. |

Example:
```bash
python simulator.py --scenario id_walk_only --max-requests 50
python simulator.py --scenario decoy_only --token-budget 25000
```

---

## Stopping Conditions

The simulator stops immediately when **any** of these 4 conditions is met:
1. **Token Budget Reached**: Context window filled (default: `50,000` tokens).
2. **Request Cap Reached**: Maximum requests sent (default: `200` requests).
3. **Session Time Cap**: Maximum wall-clock time elapsed (default: `120` seconds).
4. **IP Blocked**: HTTP 403 response with `"temporarily blocked"` in the message body. *(Note: Role-based 403s like `/users/` are correctly treated as permission denials and do not trigger a stop).*

---

## CLI Options

```text
--target         Target base URL (default: http://127.0.0.1:8000)
--scenario       Attack scenario: mixed | id_walk_only | pagination_only | decoy_only | search_only
--token-budget   Context token budget before halting (default: 50000)
--max-requests   Maximum requests cap (default: 200)
--time-cap       Maximum session duration in seconds (default: 120)
--delay          Delay between requests in seconds (default: 0.05)
--username       Authentication username (default: hr)
--password       Authentication password (default: HR@123)
```

---

## Output Reports

Every run produces a structured JSON report saved in the `reports/` directory:
- Path: `reports/run_<YYYYMMDD_HHMMSS>_<scenario>.json`
- Contains:
  - Exact execution metadata, duration, and stop reason.
  - Token consumption and tokenizer method used.
  - Count of real records vs. fake/synthetic records gathered.
  - Full request-by-request trace log.

