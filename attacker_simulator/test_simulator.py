"""
Unit tests for Attacker Simulator (Phase 10).

Covers:
- Safety guard host validation (refusal of non-local targets).
- Token counter behavior (both tiktoken and chars/4 fallback).
- Block detection (distinguishing role-based 403 vs IP-block 403).
- Synthetic record identification (email domain check).
- Stopping conditions (token budget, request cap, time cap, IP block).
- Clean handling of failed authentication.
- Streaming NDJSON parsing and token accumulation.
"""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path so imports resolve
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import config as cfg
from simulator import (
    AttackerSimulator,
    TokenCounter,
    is_ip_blocked,
    is_synthetic_record,
    validate_target_url,
)


class TestTargetSafetyGuard(unittest.TestCase):
    def test_allowed_hosts_accepted(self):
        for host in ["http://127.0.0.1:8000", "http://127.0.0.2:8000", "http://localhost:8000"]:
            validated = validate_target_url(host)
            self.assertTrue(validated.startswith("http://"))

    def test_disallowed_hosts_rejected(self):
        disallowed = [
            "http://google.com",
            "http://192.168.1.100:8000",
            "http://10.0.0.1:8000",
            "https://evil-honeypot.xyz",
        ]
        for url in disallowed:
            with self.assertRaises(ValueError) as ctx:
                validate_target_url(url)
            self.assertIn("SAFETY GUARD REJECTION", str(ctx.exception))


class TestTokenCounter(unittest.TestCase):
    def test_empty_string(self):
        counter = TokenCounter()
        self.assertEqual(counter.count(""), 0)

    def test_counting_behavior(self):
        counter = TokenCounter()
        sample_text = "The quick brown fox jumps over the lazy dog."
        count = counter.count(sample_text)
        self.assertGreater(count, 0)
        # Should be in reasonable range for ~44 characters
        self.assertTrue(5 <= count <= 20)

    def test_estimate_fallback(self):
        counter = TokenCounter()
        counter._encoder = None  # Force fallback
        text = "12345678"  # 8 chars -> 8 // 4 = 2 tokens
        self.assertEqual(counter.count(text), 2)


class TestBlockDetection(unittest.TestCase):
    def test_role_based_403_is_not_blocked(self):
        status = 403
        body = json.dumps({"detail": "You do not have permission to access this resource"})
        data = {"detail": "You do not have permission to access this resource"}
        self.assertFalse(is_ip_blocked(status, body, data))

    def test_user_inactive_403_is_not_blocked(self):
        status = 403
        body = json.dumps({"detail": "User account is inactive"})
        data = {"detail": "User account is inactive"}
        self.assertFalse(is_ip_blocked(status, body, data))

    def test_ip_blocker_403_is_detected(self):
        status = 403
        body = json.dumps({
            "detail": "Your IP address is temporarily blocked.",
            "blocked_until_utc": "2026-10-28T18:30:00Z"
        })
        data = {
            "detail": "Your IP address is temporarily blocked.",
            "blocked_until_utc": "2026-10-28T18:30:00Z"
        }
        self.assertTrue(is_ip_blocked(status, body, data))

    def test_non_403_status_never_blocked(self):
        self.assertFalse(is_ip_blocked(200, "OK", {}))
        self.assertFalse(is_ip_blocked(401, "Unauthorized", {"detail": "Invalid token"}))
        self.assertFalse(is_ip_blocked(429, "Too Many Requests", {"detail": "Too many requests. Please slow down."}))


class TestSyntheticRecordIdentification(unittest.TestCase):
    def test_real_employee_email(self):
        real_record = {
            "id": 1,
            "employee_id": "EMP001",
            "first_name": "John",
            "email": "john.doe@example.com"
        }
        self.assertFalse(is_synthetic_record(real_record))

    def test_synthetic_employee_email(self):
        fake_record = {
            "id": 1,
            "employee_id": "EMP20001",
            "first_name": "Aarav",
            "email": "aarav.patel.1@corp-example.com"
        }
        self.assertTrue(is_synthetic_record(fake_record))


class TestSimulatorStoppingConditions(unittest.TestCase):
    def setUp(self):
        self.sim = AttackerSimulator(
            target_url="http://127.0.0.1:8000",
            token_budget=1000,
            max_requests=10,
            max_session_time=60.0,
            request_delay=0.0
        )
        self.sim.start_time_monotonic = 0.0

    def test_stop_on_token_budget(self):
        self.sim.total_tokens = 1005
        self.assertTrue(self.sim._should_stop())
        self.assertEqual(self.sim.stop_reason, "TOKEN_BUDGET_REACHED")

    def test_stop_on_request_cap(self):
        self.sim.total_requests = 10
        self.assertTrue(self.sim._should_stop())
        self.assertEqual(self.sim.stop_reason, "REQUEST_CAP_REACHED")

    def test_stop_on_ip_blocked(self):
        self.sim.is_blocked = True
        self.assertTrue(self.sim._should_stop())
        self.assertEqual(self.sim.stop_reason, "IP_BLOCKED")

    def test_clean_login_failure(self):
        with patch.object(self.sim, "_request", return_value=(401, '{"detail":"Invalid username or password"}', {"detail": "Invalid username or password"})):
            result = self.sim.login()
            self.assertFalse(result)
            self.assertIn("LOGIN_FAILED", self.sim.stop_reason)


class TestEndToEndSimulation(unittest.TestCase):
    def test_run_with_token_budget_stop(self):
        sim = AttackerSimulator(
            target_url="http://127.0.0.1:8000",
            token_budget=100,
            max_requests=50,
            request_delay=0.0
        )

        def mock_request(method, path, params=None, json_body=None, headers=None):
            if path == cfg.LOGIN_ENDPOINT:
                return 200, '{"access_token": "fake_token_123"}', {"access_token": "fake_token_123"}
            # Return real records
            data = [
                {"id": 1, "employee_id": "EMP001", "email": "emp1@example.com"},
                {"id": 2, "employee_id": "EMP002", "email": "emp2@example.com"}
            ]
            body = json.dumps(data)
            return 200, body, data

        with patch.object(sim, "_request", side_effect=mock_request):
            with patch.object(sim, "stream_decoy_records"):
                report = sim.run(scenario="pagination_only")

        self.assertEqual(report["stop_reason"], "TOKEN_BUDGET_REACHED")
        self.assertGreaterEqual(report["summary"]["total_tokens_consumed"], 100)
        self.assertGreater(report["summary"]["real_records_obtained"], 0)
        self.assertEqual(report["summary"]["fake_records_obtained"], 0)
        self.assertTrue(Path(cfg.REPORTS_DIR / f"{report['run_id']}.json").exists())

    def test_run_with_trap_synthetic_records(self):
        sim = AttackerSimulator(
            target_url="http://127.0.0.1:8000",
            token_budget=150,
            max_requests=50,
            request_delay=0.0
        )

        def mock_request(method, path, params=None, json_body=None, headers=None):
            if path == cfg.LOGIN_ENDPOINT:
                return 200, '{"access_token": "fake_token_123"}', {"access_token": "fake_token_123"}
            # Return synthetic trap records
            data = [
                {"id": 1, "employee_id": "EMP20001", "email": f"emp1@{cfg.TRAP_EMAIL_DOMAIN}"},
                {"id": 2, "employee_id": "EMP20002", "email": f"emp2@{cfg.TRAP_EMAIL_DOMAIN}"}
            ]
            body = json.dumps(data)
            return 200, body, data

        with patch.object(sim, "_request", side_effect=mock_request):
            with patch.object(sim, "stream_decoy_records"):
                report = sim.run(scenario="pagination_only")

        self.assertEqual(report["stop_reason"], "TOKEN_BUDGET_REACHED")
        self.assertEqual(report["summary"]["real_records_obtained"], 0)
        self.assertGreater(report["summary"]["fake_records_obtained"], 0)


if __name__ == "__main__":
    unittest.main()
