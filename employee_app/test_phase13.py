"""
Unit tests for Phase 13 (Automated Experiment Runner & Comparative Benchmarking).

Tests:
1. Experiment lifecycle: start_experiment and finish_experiment.
2. System metric tagging and peak/avg telemetry computation.
3. Comparative analysis logic: Baseline vs Treatment data protection and resource deltas.
4. REST API endpoints:
   - POST /admin/security/experiments/start
   - POST /admin/security/experiments/{id}/finish
   - GET /admin/security/experiments
   - GET /admin/security/experiments/compare
   - POST /admin/security/experiments/set-trap
"""

import json
from pathlib import Path
import sys
import unittest

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fastapi.testclient import TestClient
from main import app
from models.security import ExperimentRun, SystemMetric
from security_database import SecuritySessionLocal, utcnow
from services import experiment_service, system_metrics_service
from services.auth_service import create_access_token


class TestExperimentService(unittest.TestCase):
    def test_experiment_lifecycle_and_telemetry_tally(self):
        db = SecuritySessionLocal()
        try:
            # 1. Start run
            run = experiment_service.start_experiment(
                name="Test Run Baseline",
                trap_enabled=False,
                db=db,
            )
            self.assertIsNotNone(run.id)
            self.assertEqual(run.name, "Test Run Baseline")
            self.assertFalse(run.trap_enabled)

            # 2. Add some tagged system metrics
            m1 = SystemMetric(timestamp=utcnow(), cpu_percent=12.5, memory_percent=65.0, run_id=run.id)
            m2 = SystemMetric(timestamp=utcnow(), cpu_percent=25.0, memory_percent=70.0, run_id=run.id)
            db.add_all([m1, m2])
            db.commit()

            # 3. Finish run with mock simulator report
            sim_report = {
                "stop_reason": "TOKEN_BUDGET_REACHED",
                "summary": {
                    "total_requests": 40,
                    "total_tokens_consumed": 30000,
                    "real_records_obtained": 150,
                    "fake_records_obtained": 0,
                },
            }
            finished = experiment_service.finish_experiment(
                run_id=run.id,
                sim_report=sim_report,
                db=db,
            )

            self.assertIsNotNone(finished.ended_at)
            self.assertEqual(finished.total_requests, 40)
            self.assertEqual(finished.total_tokens, 30000)
            self.assertEqual(finished.real_records_served, 150)
            self.assertEqual(finished.fake_records_served, 0)
            self.assertEqual(finished.peak_cpu_percent, 25.0)
            self.assertEqual(finished.peak_memory_percent, 70.0)
            self.assertEqual(finished.stop_reason, "TOKEN_BUDGET_REACHED")
        finally:
            db.close()

    def test_compare_runs_calculation(self):
        db = SecuritySessionLocal()
        try:
            # Baseline: 200 real records stolen, 0 fake
            b = ExperimentRun(
                name="Baseline",
                mode="baseline",
                trap_enabled=False,
                started_at=utcnow(),
                ended_at=utcnow(),
                total_requests=50,
                total_tokens=20000,
                real_records_served=200,
                fake_records_served=0,
                peak_cpu_percent=5.0,
                peak_memory_percent=60.0,
                stop_reason="TOKEN_BUDGET_REACHED",
            )
            # Treatment: 0 real records stolen, 300 fake records injected
            t = ExperimentRun(
                name="Treatment",
                mode="trap",
                trap_enabled=True,
                started_at=utcnow(),
                ended_at=utcnow(),
                total_requests=25,
                total_tokens=30000,
                real_records_served=0,
                fake_records_served=300,
                peak_cpu_percent=6.2,
                peak_memory_percent=60.5,
                stop_reason="TOKEN_BUDGET_REACHED",
            )
            db.add_all([b, t])
            db.commit()
            db.refresh(b)
            db.refresh(t)

            comp = experiment_service.compare_runs(b.id, t.id, db)
            self.assertIn("baseline", comp)
            self.assertIn("treatment", comp)
            self.assertIn("analysis", comp)

            analysis = comp["analysis"]
            # 100% data protection
            self.assertEqual(analysis["real_data_protected_percent"], 100.0)
            self.assertEqual(analysis["real_records_stolen_baseline"], 200)
            self.assertEqual(analysis["real_records_stolen_treatment"], 0)
            self.assertEqual(analysis["fake_records_injected"], 300)
            self.assertEqual(analysis["peak_cpu_delta"], 1.2)
        finally:
            db.close()


class TestExperimentEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_token = create_access_token(user_id=2, username="admin", role="admin")
        self.hr_token = create_access_token(user_id=4, username="hr", role="hr")

    def test_admin_auth_enforced(self):
        # Non-admin rejected
        resp = self.client.get(
            "/admin/security/experiments",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        self.assertEqual(resp.status_code, 403)

    def test_experiment_endpoints_workflow(self):
        headers = {"Authorization": f"Bearer {self.admin_token}"}

        # 1. Toggle trap
        resp = self.client.post("/admin/security/experiments/set-trap", json={"enabled": True}, headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["trap_enabled"])

        # 2. Start Baseline run
        start_resp = self.client.post(
            "/admin/security/experiments/start",
            json={"name": "API Baseline", "trap_enabled": False},
            headers=headers,
        )
        self.assertEqual(start_resp.status_code, 200)
        b_id = start_resp.json()["id"]

        # 3. Finish Baseline run
        finish_resp = self.client.post(
            f"/admin/security/experiments/{b_id}/finish",
            json={"simulator_report": {"summary": {"total_requests": 15, "total_tokens_consumed": 5000, "real_records_obtained": 30, "fake_records_obtained": 0}, "stop_reason": "REQUEST_CAP"}},
            headers=headers,
        )
        self.assertEqual(finish_resp.status_code, 200)

        # 4. Start Treatment run
        start_t_resp = self.client.post(
            "/admin/security/experiments/start",
            json={"name": "API Treatment", "trap_enabled": True},
            headers=headers,
        )
        t_id = start_t_resp.json()["id"]

        # 5. Finish Treatment run
        self.client.post(
            f"/admin/security/experiments/{t_id}/finish",
            json={"simulator_report": {"summary": {"total_requests": 10, "total_tokens_consumed": 25000, "real_records_obtained": 0, "fake_records_obtained": 200}, "stop_reason": "TOKEN_BUDGET"}},
            headers=headers,
        )

        # 6. Compare runs
        comp_resp = self.client.get(
            f"/admin/security/experiments/compare?baseline_id={b_id}&treatment_id={t_id}",
            headers=headers,
        )
        self.assertEqual(comp_resp.status_code, 200)
        data = comp_resp.json()
        self.assertEqual(data["analysis"]["real_data_protected_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
