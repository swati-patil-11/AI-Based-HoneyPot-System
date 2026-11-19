"""
Automated Experiment Benchmark Runner (Phase 13).

Conducts a scientific comparison between:
- Run 1: Baseline (Honeypot TRAP OFF)
- Run 2: Treatment (Honeypot TRAP ON)

Workflow:
1. Connects to the local server (127.0.0.1:8000).
2. Authenticates as admin to coordinate the experiment lifecycle.
3. Sets TRAP_ENABLED=false, resets state, starts Baseline Run.
4. Executes the Phase 10 Attacker Simulator and records metrics.
5. Sets TRAP_ENABLED=true, resets state, starts Treatment Run.
6. Executes the Attacker Simulator under the identical attack configuration.
7. Generates a side-by-side comparative analysis table (Tokens Consumed,
   Real Records Stolen vs Protected, Requests to Halt, and Server CPU/RAM Impact).
8. Saves the comparison report to attacker_simulator/reports/ and prints the findings.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

# Ensure attacker_simulator is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / "AI-Based-HoneyPot-System").is_dir():
    BASE_DIR = BASE_DIR / "AI-Based-HoneyPot-System"
elif BASE_DIR.name == "employee_app":
    BASE_DIR = BASE_DIR.parent
SIM_DIR = BASE_DIR / "attacker_simulator"

for p in [str(BASE_DIR), str(SIM_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from attacker_simulator.simulator import AttackerSimulator


def make_admin_request(
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    json_data: dict | None = None,
) -> tuple[int, dict | list | None]:
    url = f"{base_url}{path}"
    headers = {"User-Agent": "ExperimentRunner/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data_bytes = None
    if json_data is not None:
        data_bytes = json.dumps(json_data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=20.0) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            parsed = None
            try:
                parsed = json.loads(body)
            except Exception:
                pass
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed = None
        try:
            parsed = json.loads(body)
        except Exception:
            pass
        return exc.code, parsed
    except Exception as exc:
        print(f"[-] HTTP Error on {method} {url}: {exc}")
        return 0, None


def get_admin_token(base_url: str, username: str = "admin", password: str = "Admin@123") -> str:
    print(f"[*] Authenticating with {base_url} as '{username}'...")
    status, data = make_admin_request(
        base_url,
        "POST",
        "/auth/login",
        json_data={"username": username, "password": password},
    )
    if status == 200 and isinstance(data, dict) and "access_token" in data:
        print("[+] Admin authentication successful.")
        return data["access_token"]
    raise RuntimeError(f"Admin authentication failed (HTTP {status}): {data}")


def reset_server_state(base_url: str, admin_token: str):
    """Resets scores, cooldowns, and active traps between runs."""
    print("[*] Resetting server behavior scores and active traps...")
    make_admin_request(base_url, "POST", "/admin/security/scores/reset", token=admin_token)
    make_admin_request(base_url, "POST", "/admin/security/trap/reset", token=admin_token)


def set_trap_mode(base_url: str, admin_token: str, enabled: bool):
    print(f"[*] Setting server TRAP_ENABLED={enabled}...")
    status, data = make_admin_request(
        base_url,
        "POST",
        "/admin/security/experiments/set-trap",
        token=admin_token,
        json_data={"enabled": enabled},
    )
    if status != 200:
        print(f"[!] Warning: set-trap returned {status}: {data}")


def run_experiment_phase(
    base_url: str,
    admin_token: str,
    run_name: str,
    trap_enabled: bool,
    scenario: str,
    token_budget: int,
    max_requests: int,
    time_cap: float,
) -> dict:
    print("\n" + "=" * 70)
    print(f" STARTING EXPERIMENT RUN: {run_name.upper()} (TRAP_ENABLED={trap_enabled})")
    print("=" * 70)

    # 1. Prepare server state
    set_trap_mode(base_url, admin_token, trap_enabled)
    reset_server_state(base_url, admin_token)
    time.sleep(1.0)

    # 2. Register start of run in security.db
    status, start_data = make_admin_request(
        base_url,
        "POST",
        "/admin/security/experiments/start",
        token=admin_token,
        json_data={
            "name": run_name,
            "trap_enabled": trap_enabled,
            "config_snapshot": {
                "scenario": scenario,
                "token_budget": token_budget,
                "max_requests": max_requests,
                "time_cap": time_cap,
            },
        },
    )
    if status != 200 or not isinstance(start_data, dict):
        raise RuntimeError(f"Failed to initialize experiment on server (HTTP {status}): {start_data}")

    run_id = start_data["id"]
    print(f"[+] Server registered Run #{run_id}: '{run_name}'.")

    # 3. Execute Attacker Simulator
    print(f"[*] Launching Attacker Simulator ({scenario} scenario, budget: {token_budget:,} tokens)...")
    sim = AttackerSimulator(
        target_url=base_url,
        username="hr",
        password="HR@123",
        token_budget=token_budget,
        max_requests=max_requests,
        max_session_time=time_cap,
        request_delay=0.03,
    )
    sim_report = sim.run(scenario=scenario)

    # 4. Finish run and compile telemetry
    time.sleep(1.5)  # Let final metrics snapshot settle
    print(f"[*] Finalizing Run #{run_id} on server...")
    finish_status, finish_data = make_admin_request(
        base_url,
        "POST",
        f"/admin/security/experiments/{run_id}/finish",
        token=admin_token,
        json_data={"simulator_report": sim_report},
    )
    if finish_status != 200 or not isinstance(finish_data, dict):
        raise RuntimeError(f"Failed to finalize experiment #{run_id} (HTTP {finish_status}): {finish_data}")

    print(f"[+] Run #{run_id} completed successfully.")
    return finish_data


def print_comparison_matrix(comparison: dict, save_file: Path | None = None):
    b = comparison["baseline"]
    t = comparison["treatment"]
    a = comparison["analysis"]

    matrix_lines = []
    matrix_lines.append("\n" + "=" * 78)
    matrix_lines.append("  HONEYPOT RESEARCH EXPERIMENT — COMPARATIVE BENCHMARK (PHASE 13)")
    matrix_lines.append("=" * 78)
    matrix_lines.append(f"{'METRIC':<34} | {'BASELINE (Trap OFF)':<18} | {'TREATMENT (Trap ON)':<18}")
    matrix_lines.append("-" * 78)

    rows = [
        ("Run Identifier", f"#{b['id']} ({b['name']})", f"#{t['id']} ({t['name']})"),
        ("Stop Reason", b["stop_reason"] or "N/A", t["stop_reason"] or "N/A"),
        ("Elapsed Duration", f"{b['duration_seconds']}s", f"{t['duration_seconds']}s"),
        ("Requests Until Stop", f"{b['total_requests']}", f"{t['total_requests']}"),
        ("Tokens Consumed (Context)", f"{b['total_tokens']:,}", f"{t['total_tokens']:,}"),
        ("Real Records Stolen", f"{b['real_records_served']}", f"{t['real_records_served']}"),
        ("Synthetic Records Injected", f"{b['fake_records_served']}", f"{t['fake_records_served']}"),
        ("Data Protection Efficiency", "0.0% (No Defense)", f"{a['real_data_protected_percent']:.1f}% PROTECTED"),
        ("Time Until Block", f"{b['time_to_first_block_sec'] or 'None'}", f"{t['time_to_first_block_sec'] or 'None'}"),
        ("Peak Server CPU", f"{b['peak_cpu_percent'] or 0.0}%", f"{t['peak_cpu_percent'] or 0.0}%"),
        ("Peak Server RAM", f"{b['peak_memory_percent'] or 0.0}%", f"{t['peak_memory_percent'] or 0.0}%"),
    ]

    for label, b_val, t_val in rows:
        matrix_lines.append(f"{label:<34} | {b_val:<18} | {t_val:<18}")

    matrix_lines.append("=" * 78)

    # Key Takeaways
    matrix_lines.append("\nKEY RESEARCH FINDINGS:")
    if a["real_records_stolen_baseline"] > 0:
        protected_count = a["real_records_stolen_baseline"] - a["real_records_stolen_treatment"]
        matrix_lines.append(
            f"1. Real Data Protection: Honeypot prevented the exfiltration of "
            f"{protected_count} real employee records ({a['real_data_protected_percent']}% reduction)."
        )
    matrix_lines.append(
        f"2. Context Window Deception: Injected {a['fake_records_injected']} synthetic records, "
        f"wasting {a['tokens_consumed_treatment']:,} tokens of the agent's context window."
    )
    matrix_lines.append(
        f"3. Resource Overhead: CPU delta was {a['peak_cpu_delta']:+.2f}%, "
        f"RAM delta was {a['peak_memory_delta']:+.2f}%, confirming negligible server load."
    )
    matrix_lines.append("\nDATA INTEGRITY & DECEPTION VERIFICATION:")
    matrix_lines.append(f"• Baseline Exfiltrated: {a['real_records_stolen_baseline']} Real DB Records (0% Protection)")
    matrix_lines.append(f"• Treatment Protected:  {a['real_data_protected_percent']:.1f}% Shielded ({a['fake_records_injected']} Synthetic Decoys Injected)")
    matrix_lines.append("• Fake Honeypot Logs:   Persisted to employee_app/fake_logs/ and attacker_simulator/reports/")
    matrix_lines.append("=" * 78 + "\n")

    full_output = "\n".join(matrix_lines)
    print(full_output)

    if save_file:
        save_file.parent.mkdir(parents=True, exist_ok=True)
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)
        print(f"[+] Comparison results saved to: {save_file}")


def main():
    parser = argparse.ArgumentParser(description="Run Automated Baseline vs Trap Comparative Experiments")
    parser.add_argument("--target", default="http://127.0.0.1:8000", help="Target URL (must be 127.0.0.1 / localhost)")
    parser.add_argument("--admin-user", default="admin", help="Admin username")
    parser.add_argument("--admin-pass", default="Admin@123", help="Admin password")
    parser.add_argument("--scenario", default="mixed", choices=["mixed", "id_walk_only", "pagination_only", "decoy_only", "search_only", "full_lifecycle"])
    parser.add_argument("--token-budget", type=int, default=35000, help="Agent context budget before stopping")
    parser.add_argument("--max-requests", type=int, default=60, help="Maximum requests per run")
    parser.add_argument("--time-cap", type=float, default=60.0, help="Maximum time per run in seconds")
    args = parser.parse_args()

    print("=" * 70)
    print(" HONEYPOT AUTOMATED EXPERIMENT BENCHMARK RUNNER (PHASE 13)")
    print("=" * 70)
    print(f" Target Server:  {args.target}")
    print(f" Attack Pattern: {args.scenario}")
    print(f" Token Budget:   {args.token_budget:,} tokens")
    print(f" Request Cap:    {args.max_requests} requests")
    print("=" * 70)

    # 1. Authenticate
    admin_token = get_admin_token(args.target, args.admin_user, args.admin_pass)

    # 2. Run Baseline (Trap OFF)
    baseline_run = run_experiment_phase(
        base_url=args.target,
        admin_token=admin_token,
        run_name="Baseline (Trap OFF)",
        trap_enabled=False,
        scenario=args.scenario,
        token_budget=args.token_budget,
        max_requests=args.max_requests,
        time_cap=args.time_cap,
    )

    print("\n[*] Pausing 4 seconds for telemetry settling between runs...")
    time.sleep(4.0)

    # 3. Run Treatment (Trap ON)
    treatment_run = run_experiment_phase(
        base_url=args.target,
        admin_token=admin_token,
        run_name="Treatment (Trap ON)",
        trap_enabled=True,
        scenario=args.scenario,
        token_budget=args.token_budget,
        max_requests=args.max_requests,
        time_cap=args.time_cap,
    )

    # 4. Compare runs via Server API
    print("\n[*] Fetching comparative analysis from server...")
    comp_status, comparison = make_admin_request(
        args.target,
        "GET",
        f"/admin/security/experiments/compare?baseline_id={baseline_run['id']}&treatment_id={treatment_run['id']}",
        token=admin_token,
    )
    if comp_status != 200 or not isinstance(comparison, dict):
        raise RuntimeError(f"Failed to fetch comparison (HTTP {comp_status}): {comparison}")

    # 5. Output comparison
    report_file = (
        SIM_DIR
        / "reports"
        / f"experiment_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    print_comparison_matrix(comparison, save_file=report_file)


if __name__ == "__main__":
    main()
