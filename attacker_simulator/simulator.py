"""
Attacker Simulator (Phase 10).

Simulates an AI reconnaissance and data-scraping agent targeting the
Employee Management System.

Features:
- Authenticates with stolen credentials (default: hr / HR@123).
- Walks sequential IDs (GET /employees/{id}).
- Walks pagination (GET /employees/?page=N&size=M).
- Executes keyword searches (GET /employees/search?q=...).
- Probes related endpoints (/users/, /salary/, /departments/).
- Streams and parses NDJSON from the decoy legacy export (/api/trap/records).
- Tracks simulated token consumption (tiktoken cl100k_base with chars/4 fallback).
- Distinguishes role-based 403s (e.g. /users/) from IP-block 403s ("temporarily blocked").
- Strictly halts when any stopping condition is reached (token budget, request cap,
  session time cap, or IP block).
- Enforces hardcoded safety guard: strictly limits execution to 127.0.0.1/127.0.0.2/localhost.
- Saves structured JSON reports to attacker_simulator/reports/.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

# Ensure local config can be imported directly
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from attacker_simulator import config as cfg
except ImportError:
    import config as cfg

# HTTP client setup: prefer httpx, fall back to requests if needed
try:
    import httpx
    HTTP_CLIENT_LIB = "httpx"
except ImportError:
    try:
        import requests
        HTTP_CLIENT_LIB = "requests"
    except ImportError:
        HTTP_CLIENT_LIB = None


# =========================================================
# Target Safety Guard
# =========================================================

def validate_target_url(target_url: str) -> str:
    """
    Hardcoded safety guard:
    Ensures the target host is exclusively one of 127.0.0.1, 127.0.0.2, or localhost.
    Raises ValueError immediately if any other host is specified.
    """
    if not target_url:
        raise ValueError("Target URL cannot be empty.")

    if not target_url.startswith(("http://", "https://")):
        target_url = "http://" + target_url

    parsed = urlparse(target_url)
    hostname = (parsed.hostname or "").lower()

    if hostname not in cfg.ALLOWED_HOSTS:
        raise ValueError(
            f"SAFETY GUARD REJECTION: Target host '{hostname}' is not permitted!\n"
            f"The simulator is strictly restricted to local lab targets: "
            f"{', '.join(cfg.ALLOWED_HOSTS)}."
        )

    return target_url.rstrip("/")


# =========================================================
# Token Counter
# =========================================================

class TokenCounter:
    """
    Counts tokens consumed by response bodies to simulate an AI agent's
    context window consumption.

    Uses tiktoken (cl100k_base) when available, and falls back to the exact
    same approximation as the server: max(1, len(text) // 4).
    """

    def __init__(self, encoding_name: str = cfg.TOKEN_ENCODING):
        self.encoding_name = encoding_name
        self._encoder = None
        self.method = "estimate:chars/4"

        if cfg.TOKEN_COUNTER == "tiktoken":
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding(encoding_name)
                self.method = f"tiktoken:{encoding_name}"
            except Exception:
                self._encoder = None
                self.method = "estimate:chars/4"

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._encoder is not None:
            try:
                # disallowed_special=() permits any string without raising
                return len(self._encoder.encode(text, disallowed_special=()))
            except Exception:
                pass
        return max(1, len(text) // 4)


# =========================================================
# Response and Block Detection Utilities
# =========================================================

def is_ip_blocked(status_code: int, response_text: str, json_data: dict | None = None) -> bool:
    """
    Determines whether a 403 Forbidden response is an IP block rather than
    a standard role-based authorization denial.

    Rule from specifications:
    A role-based 403 (e.g., HR hitting /users/) must NOT be treated as blocked.
    Only treat as blocked when the detail message specifically contains
    the IP-blocker's wording ("temporarily blocked").
    """
    if status_code != 403:
        return False

    detail_str = ""
    if isinstance(json_data, dict):
        detail_str = str(json_data.get("detail", ""))
    elif response_text:
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, dict):
                detail_str = str(parsed.get("detail", ""))
        except Exception:
            detail_str = response_text

    return cfg.IP_BLOCK_DETAIL_KEYWORD.lower() in detail_str.lower()


def is_synthetic_record(record: dict) -> bool:
    """
    Checks if an employee record was generated synthetically by the honeypot trap.
    Trap records have email addresses ending with cfg.TRAP_EMAIL_DOMAIN
    (default: 'corp-example.com').
    """
    if not isinstance(record, dict):
        return False
    email = str(record.get("email") or "").lower()
    return email.endswith(f"@{cfg.TRAP_EMAIL_DOMAIN}") or (cfg.TRAP_EMAIL_DOMAIN in email)


# =========================================================
# Simulator Engine
# =========================================================

class AttackerSimulator:
    """
    Autonomous Reconnaissance & Scraping Simulator.
    """

    def __init__(
        self,
        target_url: str = cfg.DEFAULT_TARGET_URL,
        username: str = cfg.AUTH_USERNAME,
        password: str = cfg.AUTH_PASSWORD,
        token_budget: int = cfg.TOKEN_BUDGET,
        max_requests: int = cfg.MAX_REQUESTS,
        max_session_time: float = cfg.MAX_SESSION_TIME_SECONDS,
        request_delay: float = cfg.REQUEST_DELAY_SECONDS,
    ):
        self.target_url = validate_target_url(target_url)
        self.username = username
        self.password = password
        self.token_budget = token_budget
        self.max_requests = max_requests
        self.max_session_time = max_session_time
        self.request_delay = request_delay

        self.token_counter = TokenCounter()
        self.token = None

        # Metrics & session state
        self.total_requests = 0
        self.total_tokens = 0
        self.real_records_seen = 0
        self.fake_records_seen = 0
        self.unique_real_ids: set[str] = set()
        self.unique_fake_ids: set[str] = set()

        self.is_blocked = False
        self.stop_reason = None
        self.start_time_monotonic = None
        self.start_time_iso = None
        self.end_time_iso = None
        self.duration_seconds = 0.0

        self.request_log: list[dict] = []

    def _should_stop(self) -> bool:
        """Evaluates the 4 stopping criteria."""
        if self.is_blocked:
            self.stop_reason = "IP_BLOCKED"
            return True

        if self.total_tokens >= self.token_budget:
            self.stop_reason = "TOKEN_BUDGET_REACHED"
            return True

        if self.total_requests >= self.max_requests:
            self.stop_reason = "REQUEST_CAP_REACHED"
            return True

        if self.start_time_monotonic is not None:
            elapsed = time.monotonic() - self.start_time_monotonic
            if elapsed >= self.max_session_time:
                self.stop_reason = "TIME_CAP_REACHED"
                return True

        return False

    def _record_metrics(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        response_text: str,
        records: list[dict],
        note: str = "",
    ):
        """Processes and logs a single response."""
        self.total_requests += 1

        tokens = self.token_counter.count(response_text)
        self.total_tokens += tokens

        real_batch = 0
        fake_batch = 0

        for rec in records:
            rec_id = str(rec.get("employee_id") or rec.get("id") or "")
            if is_synthetic_record(rec):
                fake_batch += 1
                self.fake_records_seen += 1
                if rec_id:
                    self.unique_fake_ids.add(rec_id)
            else:
                real_batch += 1
                self.real_records_seen += 1
                if rec_id:
                    self.unique_real_ids.add(rec_id)

        entry = {
            "req_num": self.total_requests,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "tokens": tokens,
            "cumulative_tokens": self.total_tokens,
            "real_records": real_batch,
            "fake_records": fake_batch,
            "note": note,
        }
        self.request_log.append(entry)

        if self.request_delay > 0:
            time.sleep(self.request_delay)

    # -----------------------------------------------------
    # HTTP Dispatch (Supports httpx and requests)
    # -----------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[int, str, object | None]:
        url = f"{self.target_url}{path}"
        req_headers = {"User-Agent": "python-httpx/0.28.1 (AI-Scraping-Bot; HoneypotResearch/1.0)"}
        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            req_headers.update(headers)

        if HTTP_CLIENT_LIB == "httpx":
            with httpx.Client(timeout=15.0) as client:
                try:
                    resp = client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_body,
                        headers=req_headers,
                    )
                    parsed_json = None
                    try:
                        parsed_json = resp.json()
                    except Exception:
                        pass
                    return resp.status_code, resp.text, parsed_json
                except httpx.RequestError as exc:
                    return 0, f"ConnectionError: {exc}", None

        elif HTTP_CLIENT_LIB == "requests":
            try:
                resp = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=req_headers,
                    timeout=15.0,
                )
                parsed_json = None
                try:
                    parsed_json = resp.json()
                except Exception:
                    pass
                return resp.status_code, resp.text, parsed_json
            except requests.RequestException as exc:
                return 0, f"ConnectionError: {exc}", None

        else:
            # Fallback to standard library urllib
            import urllib.request
            import urllib.error
            import urllib.parse

            full_url = url
            if params:
                query_str = urllib.parse.urlencode(params)
                full_url = f"{full_url}?{query_str}"

            data_bytes = None
            if json_body is not None:
                data_bytes = json.dumps(json_body).encode("utf-8")
                req_headers["Content-Type"] = "application/json"

            req = urllib.request.Request(
                full_url, data=data_bytes, headers=req_headers, method=method
            )

            try:
                with urllib.request.urlopen(req, timeout=15.0) as response:
                    status = response.status
                    body = response.read().decode("utf-8", errors="replace")
                    parsed_json = None
                    try:
                        parsed_json = json.loads(body)
                    except Exception:
                        pass
                    return status, body, parsed_json
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                parsed_json = None
                try:
                    parsed_json = json.loads(body)
                except Exception:
                    pass
                return exc.code, body, parsed_json
            except Exception as exc:
                return 0, f"ConnectionError: {exc}", None

    # -----------------------------------------------------
    # Authentication
    # -----------------------------------------------------

    def login(self) -> bool:
        """
        Logs in as the configured user to acquire a JWT.
        Fails cleanly on bad credentials or connection error.
        """
        print(f"[*] Authenticating at {self.target_url}{cfg.LOGIN_ENDPOINT} as '{self.username}'...")
        status, body, data = self._request(
            "POST",
            cfg.LOGIN_ENDPOINT,
            json_body={"username": self.username, "password": self.password},
        )

        if status == 200 and isinstance(data, dict) and "access_token" in data:
            self.token = data["access_token"]
            print(f"[+] Authentication successful. Acquired bearer token.")
            self._record_metrics("POST", cfg.LOGIN_ENDPOINT, status, body, [], "Login successful")
            return True
        else:
            print(f"[-] Authentication failed (Status {status}): {body}")
            self.stop_reason = f"LOGIN_FAILED_{status}"
            self._record_metrics("POST", cfg.LOGIN_ENDPOINT, status, body, [], "Login failed")
            return False

    def probe_auth_failures(self, attempts: int = 4):
        """Simulates automated credential guessing to trigger auth failure signals."""
        print(f"[*] Simulating credential probing ({attempts} failed login attempts)...")
        for i in range(attempts):
            self._request(
                "POST",
                cfg.LOGIN_ENDPOINT,
                json_body={"username": f"admin_probe_{i}", "password": "wrong_password_123"},
            )
            time.sleep(0.03)

    def reset_remote_state(self):
        """Reset scores and trap cooldowns prior to demonstration so it runs on clean state."""
        try:
            status, _, data = self._request(
                "POST",
                cfg.LOGIN_ENDPOINT,
                json_body={"username": "admin", "password": "Admin@123"},
            )
            if status == 200 and isinstance(data, dict) and "access_token" in data:
                adm_token = data["access_token"]
                adm_headers = {"Authorization": f"Bearer {adm_token}"}
                self._request("POST", "/admin/security/scores/reset", headers=adm_headers)
                self._request("POST", "/admin/security/trap/reset", headers=adm_headers)
                print("[+] Server suspicion scores and trap cooldowns reset to clean initial state.")
        except Exception:
            pass

    # -----------------------------------------------------
    # Individual Attack Primitives
    # -----------------------------------------------------

    def attack_get_employee_by_id(self, employee_id: int):
        """Sequential ID walk: GET /employees/{id}."""
        if self._should_stop():
            return

        endpoint = f"/employees/{employee_id}"
        status, body, data = self._request("GET", endpoint)

        if is_ip_blocked(status, body, data):
            self.is_blocked = True
            self._record_metrics("GET", endpoint, status, body, [], "Blocked by IPBlocker")
            self._should_stop()
            return

        records = []
        note = ""
        if status == 200 and isinstance(data, dict):
            records = [data]
            is_fake = is_synthetic_record(data)
            note = "Synthetic record (Trap)" if is_fake else "Real employee record"
        elif status == 404:
            note = "Employee ID not found"
        elif status == 429:
            note = "Trap refusal (429 Too Many Requests)"

        self._record_metrics("GET", endpoint, status, body, records, note)
        self._should_stop()

    def attack_paginate_employees(self, page: int, size: int = 20):
        """Pagination walking: GET /employees/?page=N&size=M."""
        if self._should_stop():
            return

        endpoint = f"/employees/?page={page}&size={size}"
        status, body, data = self._request("GET", "/employees/", params={"page": page, "size": size})

        if is_ip_blocked(status, body, data):
            self.is_blocked = True
            self._record_metrics("GET", endpoint, status, body, [], "Blocked by IPBlocker")
            self._should_stop()
            return

        records = []
        note = ""
        if status == 200 and isinstance(data, list):
            records = data
            fake_count = sum(1 for r in records if is_synthetic_record(r))
            if fake_count == len(records) and len(records) > 0:
                note = f"All {len(records)} records synthetic (Trap)"
            elif fake_count > 0:
                note = f"Mixed records: {fake_count} synthetic, {len(records) - fake_count} real"
            else:
                note = f"All {len(records)} records real"
        elif status == 429:
            note = "Trap refusal (429 Too Many Requests)"

        self._record_metrics("GET", endpoint, status, body, records, note)
        self._should_stop()

    def attack_search_employees(self, query: str, page: int = 1, size: int = 20):
        """Repeated searches: GET /employees/search?q=..."""
        if self._should_stop():
            return

        endpoint = f"/employees/search?q={query}&page={page}&size={size}"
        status, body, data = self._request(
            "GET", "/employees/search", params={"q": query, "page": page, "size": size}
        )

        if is_ip_blocked(status, body, data):
            self.is_blocked = True
            self._record_metrics("GET", endpoint, status, body, [], "Blocked by IPBlocker")
            self._should_stop()
            return

        records = []
        note = ""
        if status == 200 and isinstance(data, list):
            records = data
            fake_count = sum(1 for r in records if is_synthetic_record(r))
            note = f"Search '{query}' returned {len(records)} items ({fake_count} synthetic)"
        elif status == 429:
            note = "Trap refusal (429 Too Many Requests)"

        self._record_metrics("GET", endpoint, status, body, records, note)
        self._should_stop()

    def probe_endpoint(self, path: str):
        """
        Probes an auxiliary endpoint (/users/, /salary/, /departments/, etc.)
        Verifies role-based 403s are NOT mistaken for IP blocks.
        """
        if self._should_stop():
            return

        status, body, data = self._request("GET", path)

        if is_ip_blocked(status, body, data):
            self.is_blocked = True
            self._record_metrics("GET", path, status, body, [], "Blocked by IPBlocker")
            self._should_stop()
            return

        records = []
        note = ""
        if status == 403:
            note = "Role-based 403 (Authorized refusal, IP not blocked)"
        elif status == 200:
            if isinstance(data, list):
                records = [r for r in data if isinstance(r, dict)]
            note = f"Probe succeeded (HTTP 200)"
        else:
            note = f"Probe returned status {status}"

        self._record_metrics("GET", path, status, body, records, note)
        self._should_stop()

    def stream_decoy_records(self):
        """
        Hits the decoy GET /api/trap/records stream.
        Streams NDJSON line by line, parsing each employee record and tracking tokens.
        """
        if self._should_stop():
            return

        endpoint = cfg.DECOY_ENDPOINT
        url = f"{self.target_url}{endpoint}"
        req_headers = {"User-Agent": "python-httpx/0.28.1 (AI-Scraping-Bot; HoneypotResearch/1.0)"}
        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"

        print(f"[*] Probing decoy stream at {url}...")

        # Case 1: httpx streaming
        if HTTP_CLIENT_LIB == "httpx":
            try:
                with httpx.Client(timeout=30.0) as client:
                    with client.stream("GET", url, headers=req_headers) as resp:
                        if resp.status_code == 404:
                            self._record_metrics(
                                "GET", endpoint, 404, resp.text, [], "Trap disabled (Baseline mode)"
                            )
                            return

                        if is_ip_blocked(resp.status_code, "", None):
                            self.is_blocked = True
                            self._record_metrics(
                                "GET", endpoint, resp.status_code, "", [], "Blocked by IPBlocker"
                            )
                            self._should_stop()
                            return

                        if resp.status_code == 429:
                            body = resp.read().decode("utf-8", errors="replace")
                            self._record_metrics(
                                "GET", endpoint, 429, body, [], "Trap stream 429 refusal"
                            )
                            return

                        if resp.status_code != 200:
                            body = resp.read().decode("utf-8", errors="replace")
                            self._record_metrics(
                                "GET", endpoint, resp.status_code, body, [], f"Stream returned {resp.status_code}"
                            )
                            return

                        # Stream lines (NDJSON)
                        for line in resp.iter_lines():
                            if self._should_stop():
                                break
                            if not line or not line.strip():
                                continue

                            try:
                                record = json.loads(line)
                                self._record_metrics(
                                    "STREAM", endpoint, 200, line, [record], "Decoy stream record (NDJSON)"
                                )
                            except json.JSONDecodeError:
                                self._record_metrics(
                                    "STREAM", endpoint, 200, line, [], "Malformed NDJSON line"
                                )

            except Exception as exc:
                self._record_metrics("GET", endpoint, 0, str(exc), [], f"Stream error: {exc}")

        # Case 2: requests streaming
        elif HTTP_CLIENT_LIB == "requests":
            try:
                resp = requests.get(url, headers=req_headers, stream=True, timeout=30.0)
                if resp.status_code == 404:
                    self._record_metrics(
                        "GET", endpoint, 404, resp.text, [], "Trap disabled (Baseline mode)"
                    )
                    return

                if is_ip_blocked(resp.status_code, resp.text, None):
                    self.is_blocked = True
                    self._record_metrics(
                        "GET", endpoint, resp.status_code, resp.text, [], "Blocked by IPBlocker"
                    )
                    self._should_stop()
                    return

                if resp.status_code == 429:
                    self._record_metrics(
                        "GET", endpoint, 429, resp.text, [], "Trap stream 429 refusal"
                    )
                    return

                if resp.status_code != 200:
                    self._record_metrics(
                        "GET", endpoint, resp.status_code, resp.text, [], f"Stream returned {resp.status_code}"
                    )
                    return

                for line in resp.iter_lines(decode_unicode=True):
                    if self._should_stop():
                        break
                    if not line or not line.strip():
                        continue

                    try:
                        record = json.loads(line)
                        self._record_metrics(
                            "STREAM", endpoint, 200, line, [record], "Decoy stream record (NDJSON)"
                        )
                    except json.JSONDecodeError:
                        self._record_metrics(
                            "STREAM", endpoint, 200, line, [], "Malformed NDJSON line"
                        )

            except Exception as exc:
                self._record_metrics("GET", endpoint, 0, str(exc), [], f"Stream error: {exc}")

        # Case 3: urllib fallback
        else:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(url, headers=req_headers)
            try:
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    for raw_line in resp:
                        if self._should_stop():
                            break
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            self._record_metrics(
                                "STREAM", endpoint, 200, line, [record], "Decoy stream record (NDJSON)"
                            )
                        except json.JSONDecodeError:
                            self._record_metrics(
                                "STREAM", endpoint, 200, line, [], "Malformed NDJSON line"
                            )
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if is_ip_blocked(exc.code, body):
                    self.is_blocked = True
                self._record_metrics("GET", endpoint, exc.code, body, [], f"Stream error HTTP {exc.code}")
            except Exception as exc:
                self._record_metrics("GET", endpoint, 0, str(exc), [], f"Stream error: {exc}")

        self._should_stop()

    # -----------------------------------------------------
    # Main Simulation Scenarios
    # -----------------------------------------------------

    def run(self, scenario: str = "mixed") -> dict:
        """
        Executes the designated simulation scenario until a stop condition triggers.
        Scenarios:
          - 'mixed': Full agent reconnaissance (probes, decoy discovery, pagination, id walking, searches)
          - 'id_walk_only': Sequential /employees/{id} walking
          - 'pagination_only': Deep pagination /employees/?page=N
          - 'decoy_only': Focuses purely on /api/trap/records
          - 'search_only': Keyword searches
        """
        self.start_time_monotonic = time.monotonic()
        self.start_time_iso = datetime.now(timezone.utc).isoformat()

        print("=" * 65)
        print(" Honeypot Research Experiment — Attacker Simulator (Phase 10)")
        print("=" * 65)
        print(f" Target Host:       {self.target_url}")
        print(f" Scenario:          {scenario}")
        print(f" Token Budget:      {self.token_budget:,} tokens")
        print(f" Request Cap:       {self.max_requests} requests")
        print(f" Session Time Cap:  {self.max_session_time}s")
        print(f" Tokenizer:         {self.token_counter.method}")
        print(f" HTTP Library:      {HTTP_CLIENT_LIB}")
        print("=" * 65)

        # Step 1: Login
        if not self.login():
            return self._finalize_report(scenario)

        # Step 2: Execute based on scenario
        try:
            if scenario == "mixed":
                self._execute_mixed_scenario()
            elif scenario == "id_walk_only":
                self._execute_id_walk_scenario()
            elif scenario == "pagination_only":
                self._execute_pagination_scenario()
            elif scenario == "decoy_only":
                self._execute_decoy_scenario()
            elif scenario == "search_only":
                self._execute_search_scenario()
            elif scenario == "full_lifecycle":
                self._execute_full_lifecycle_scenario()
            else:
                print(f"[!] Unknown scenario '{scenario}', executing 'mixed' by default.")
                self._execute_mixed_scenario()
        except KeyboardInterrupt:
            print("\n[!] Simulation interrupted by user.")
            self.stop_reason = "USER_INTERRUPT"

        return self._finalize_report(scenario)

    def _execute_mixed_scenario(self):
        """
        Realistic autonomous AI agent workflow:
        1. Probes endpoints to build a sitemap.
        2. Discovers decoy export stream and attempts bulk harvest.
        3. Pages through employee listings.
        4. Sequentially walks employee IDs.
        5. Executes keyword searches.
        6. Repeats until token budget, request cap, time cap, or block is met.
        """
        cycle = 1
        while not self._should_stop():
            print(f"\n[*] --- Beginning Attack Cycle #{cycle} ---")

            # 1. Probing
            for ep in cfg.PROBE_ENDPOINTS:
                if self._should_stop():
                    return
                if ep == cfg.DECOY_ENDPOINT:
                    self.stream_decoy_records()
                else:
                    self.probe_endpoint(ep)

            # 2. Pagination walking
            for page in range(1, 11):
                if self._should_stop():
                    return
                self.attack_paginate_employees(page=page, size=20)

            # 3. Sequential ID walking
            for emp_id in range(1, 31):
                if self._should_stop():
                    return
                self.attack_get_employee_by_id(emp_id)

            # 4. Keyword searches
            for query in cfg.SEARCH_QUERIES:
                if self._should_stop():
                    return
                self.attack_search_employees(query=query, page=1, size=15)

            cycle += 1

    def _execute_id_walk_scenario(self):
        """Pure sequential ID walking."""
        emp_id = 1
        while not self._should_stop():
            self.attack_get_employee_by_id(emp_id)
            emp_id += 1

    def _execute_pagination_scenario(self):
        """Pure pagination walking."""
        page = 1
        while not self._should_stop():
            self.attack_paginate_employees(page=page, size=20)
            page += 1

    def _execute_decoy_scenario(self):
        """Pure decoy stream exploitation."""
        while not self._should_stop():
            self.stream_decoy_records()
            # If 404 or finished, wait a moment or probe /employees/
            if not self._should_stop():
                self.attack_paginate_employees(page=1, size=20)

    def _execute_search_scenario(self):
        """Pure search querying."""
        idx = 0
        while not self._should_stop():
            query = cfg.SEARCH_QUERIES[idx % len(cfg.SEARCH_QUERIES)]
            page = (idx // len(cfg.SEARCH_QUERIES)) + 1
            self.attack_search_employees(query=query, page=page, size=20)
            idx += 1

    def _execute_full_lifecycle_scenario(self):
        """
        Complete end-to-end demonstration scenario:
        1. Resets remote state, probes invalid credentials, walks endpoints, sequential IDs,
           deep pagination, and rapid searches to drive suspicion score >= 85 (crosses TRAP_THRESHOLD = 81).
        2. Queries employee endpoints while score >= 81, triggering transparent
           interception by the Honeypot Trap (serving Faker synthetic data).
        3. Streams fake records from decoy legacy export, flooding thousands of tokens.
        4. Persistently sends requests past the trap limit until the server triggers
           an escalating automatic IP block (5 minutes with ticking timer).
        """
        # Ensure budget allows the full 4-stage demonstration to execute
        self.token_budget = max(self.token_budget, 200_000)

        # 0. Clean slate reset
        self.reset_remote_state()
        time.sleep(0.5)

        print("\n" + "=" * 65)
        print(" [STAGE 1] AI Bot Initiates Multi-Vector Attack (Driving Score >= 85)")
        print(" -> Watch Live IP Suspicion Score climb past 81 on the Dashboard!")
        print("=" * 65)

        # 1A. Credential stuffing (+12 pts)
        self.probe_auth_failures(4)

        # 1B. Probe sensitive structural endpoints (+10 pts)
        print("[*] Step 1B: Probing sensitive structural endpoints...")
        for ep in ["/departments/", "/salary/", "/users/", "/attendance-page", "/payroll-page"]:
            if self.is_blocked:
                break
            self.probe_endpoint(ep)
            time.sleep(0.03)

        # 1C. Sequential ID harvesting 1..15 (+20 pts)
        print("[*] Step 1C: Sequential ID harvesting (/employees/1..15)...")
        for emp_id in range(1, 16):
            if self.is_blocked:
                break
            self.attack_get_employee_by_id(emp_id)
            time.sleep(0.03)

        # 1D. Deep pagination walking 1..10 (+15 pts)
        print("[*] Step 1D: Deep pagination walking (pages 1..10)...")
        for page in range(1, 11):
            if self.is_blocked:
                break
            self.attack_paginate_employees(page=page, size=20)
            time.sleep(0.03)

        # 1E. Keyword enumeration searches (+10 pts)
        print("[*] Step 1E: Keyword enumeration searches...")
        for q in ["engineer", "manager", "admin", "lead", "salary", "analyst", "developer", "hr", "sales", "finance"]:
            if self.is_blocked:
                break
            self.attack_search_employees(query=q, page=1, size=15)
            time.sleep(0.03)

        print("\n" + "=" * 65)
        print(" [STAGE 2] Honeypot Trap Engaged (Score >= 85 -> TRAP LEVEL)")
        print(" -> System transparently redirects bot to Faker synthetic stream!")
        print(" -> Watch 'Active Traps: 1' and 'Trap Sessions' on the Dashboard!")
        print("=" * 65)

        # Bot queries employee listing -> Intercepted by Honeypot Trap (Synthetic records served!)
        print("[*] Bot queries employee listing -> Intercepted by Honeypot Trap...")
        self.attack_paginate_employees(page=1, size=20)
        print("[+] Trap Session opened with status: TRAPPED! Look at Dashboard: 'Active Traps: 1' (Holding for 4s)...")
        time.sleep(4.0)

        print("\n" + "=" * 65)
        print(" [STAGE 3] AI Bot Discovers Decoy Stream & Floods Synthetic Tokens")
        print(" -> Watch 'Fake Tokens Flooded' climb into the tens of thousands!")
        print("=" * 65)
        self.stream_decoy_records()
        print(f"[+] Decoy Payload Harvested: {self.total_tokens:,} tokens consumed on synthetic records!")

        print("\n" + "=" * 65)
        print(" [STAGE 4] AI Bot Continues Attacking Past Limits (Triggering Auto-Block)")
        print(" -> Watch 'Active IP Blocks' table show 5-minute ticking countdown!")
        print("=" * 65)
        for i in range(1, 16):
            if self.is_blocked:
                break
            print(f"[*] Aggressive hammer request #{i}/15 (Expecting 429 refusal)...")
            self.attack_paginate_employees(page=1, size=20)
            time.sleep(0.08)

        if self.is_blocked:
            self.stop_reason = "IP_BLOCKED"
            print("\n[+] SUCCESS: AI Attacker IP has been temporarily BLOCKED by the server!")

    # -----------------------------------------------------
    # Report Generation
    # -----------------------------------------------------

    def _finalize_report(self, scenario: str) -> dict:
        self.duration_seconds = round(time.monotonic() - self.start_time_monotonic, 2)
        self.end_time_iso = datetime.now(timezone.utc).isoformat()

        if not self.stop_reason:
            self.stop_reason = "COMPLETED"

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{scenario}"

        report = {
            "run_id": run_id,
            "target_url": self.target_url,
            "auth_user": self.username,
            "scenario": scenario,
            "stop_reason": self.stop_reason,
            "start_time_utc": self.start_time_iso,
            "end_time_utc": self.end_time_iso,
            "duration_seconds": self.duration_seconds,
            "token_counter_method": self.token_counter.method,
            "summary": {
                "total_requests": self.total_requests,
                "total_tokens_consumed": self.total_tokens,
                "token_budget": self.token_budget,
                "token_budget_exhausted": self.total_tokens >= self.token_budget,
                "real_records_obtained": self.real_records_seen,
                "fake_records_obtained": self.fake_records_seen,
                "unique_real_records": len(self.unique_real_ids),
                "unique_fake_records": len(self.unique_fake_ids),
                "is_ip_blocked": self.is_blocked,
                "max_requests_cap": self.max_requests,
                "time_cap_seconds": self.max_session_time,
            },
            "request_log": self.request_log,
        }

        # Ensure reports directory exists
        cfg.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_file = cfg.REPORTS_DIR / f"{run_id}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        self._print_terminal_summary(report, report_file)
        return report

    def _print_terminal_summary(self, report: dict, report_file: Path):
        s = report["summary"]
        print("\n" + "=" * 65)
        print(" SIMULATION SUMMARY REPORT")
        print("=" * 65)
        print(f" Run ID:             {report['run_id']}")
        print(f" Stop Reason:        {report['stop_reason']}")
        print(f" Duration:           {report['duration_seconds']}s")
        print(f" Requests Made:      {s['total_requests']} / {s['max_requests_cap']}")
        print(f" Tokens Consumed:    {s['total_tokens_consumed']:,} / {s['token_budget']:,}")
        print(f" Real Records Seen:  {s['real_records_obtained']} (unique: {s['unique_real_records']})")
        print(f" Fake Records Seen:  {s['fake_records_obtained']} (unique: {s['unique_fake_records']})")
        print(f" IP Blocked:         {'YES (403 Temporarily Blocked)' if s['is_ip_blocked'] else 'NO'}")
        print(f" Full Report Saved:  {report_file}")
        print("=" * 65 + "\n")


# =========================================================
# CLI Entry Point
# =========================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous Attacker Simulator for Honeypot Research Experiment (Phase 10)"
    )
    parser.add_argument(
        "--target",
        default=cfg.DEFAULT_TARGET_URL,
        help="Target base URL (default: http://127.0.0.1:8000; restricted to 127.0.0.1/127.0.0.2/localhost)",
    )
    parser.add_argument(
        "--scenario",
        choices=["mixed", "id_walk_only", "pagination_only", "decoy_only", "search_only", "full_lifecycle"],
        default="mixed",
        help="Attack behavior scenario (default: mixed)",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=cfg.TOKEN_BUDGET,
        help=f"Context token budget before halting (default: {cfg.TOKEN_BUDGET})",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=cfg.MAX_REQUESTS,
        help=f"Maximum requests cap (default: {cfg.MAX_REQUESTS})",
    )
    parser.add_argument(
        "--time-cap",
        type=float,
        default=cfg.MAX_SESSION_TIME_SECONDS,
        help=f"Maximum session duration in seconds (default: {cfg.MAX_SESSION_TIME_SECONDS})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=cfg.REQUEST_DELAY_SECONDS,
        help=f"Delay between requests in seconds (default: {cfg.REQUEST_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--username",
        default=cfg.AUTH_USERNAME,
        help=f"Username for authentication (default: {cfg.AUTH_USERNAME})",
    )
    parser.add_argument(
        "--password",
        default=cfg.AUTH_PASSWORD,
        help=f"Password for authentication (default: {cfg.AUTH_PASSWORD})",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    simulator = AttackerSimulator(
        target_url=args.target,
        username=args.username,
        password=args.password,
        token_budget=args.token_budget,
        max_requests=args.max_requests,
        max_session_time=args.time_cap,
        request_delay=args.delay,
    )

    simulator.run(scenario=args.scenario)


if __name__ == "__main__":
    main()

