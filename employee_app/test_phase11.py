"""
Unit tests for Phase 11 (WebSocket + System Monitoring).

Tests:
1. psutil metrics sampling and storage into system_metrics table.
2. Request rate calculation (requests_per_second).
3. WebSocket manager connection, broadcast, and disconnect handling.
4. REST endpoint GET /admin/security/system-metrics.
5. WebSocket endpoint /ws/admin authorization and message exchange.
"""

import json
from pathlib import Path
import sys
import unittest

# Ensure employee_app root is in sys.path
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fastapi.testclient import TestClient
from main import app
from models.security import SystemMetric
from security_database import SecuritySessionLocal
from services import system_metrics_service
from services.auth_service import create_access_token
from services.ws_manager import manager as ws_manager


class TestSystemMetricsService(unittest.TestCase):
    def test_collect_once_saves_to_db(self):
        system_metrics_service.count_request()
        system_metrics_service.count_request()

        result = system_metrics_service.collect_once()
        self.assertIsNotNone(result)
        self.assertIn("cpu_percent", result)
        self.assertIn("memory_percent", result)
        self.assertIn("requests_per_second", result)
        self.assertIn("active_traps", result)

        db = SecuritySessionLocal()
        try:
            saved = db.get(SystemMetric, result["id"])
            self.assertIsNotNone(saved)
            self.assertEqual(saved.id, result["id"])
            self.assertGreaterEqual(saved.cpu_percent, 0.0)
            self.assertGreater(saved.memory_percent, 0.0)
        finally:
            db.close()

    def test_get_recent_metrics(self):
        db = SecuritySessionLocal()
        try:
            metrics = system_metrics_service.get_recent_metrics(db, limit=5)
            self.assertIsInstance(metrics, list)
            if metrics:
                first = metrics[0]
                self.assertIn("cpu_percent", first)
                self.assertIn("memory_percent", first)
        finally:
            db.close()


class TestSystemMetricsRESTEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_token = create_access_token(user_id=2, username="admin", role="admin")
        self.hr_token = create_access_token(user_id=4, username="hr", role="hr")

    def test_system_metrics_requires_admin(self):
        # No token
        resp = self.client.get("/admin/security/system-metrics")
        self.assertEqual(resp.status_code, 401)

        # HR token (not admin)
        resp = self.client.get(
            "/admin/security/system-metrics",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        self.assertEqual(resp.status_code, 403)

    def test_system_metrics_success_with_admin_token(self):
        resp = self.client.get(
            "/admin/security/system-metrics?limit=10",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)


class TestAdminWebSocket(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.admin_token = create_access_token(user_id=2, username="admin", role="admin")
        self.hr_token = create_access_token(user_id=4, username="hr", role="hr")

    def test_ws_rejects_unauthorized_token(self):
        # Non-admin user (HR)
        with self.assertRaises(Exception):
            with self.client.websocket_connect(f"/ws/admin?token={self.hr_token}"):
                pass

        # Invalid token
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/admin?token=invalid_token"):
                pass

    def test_ws_accepts_admin_and_receives_init_and_ping(self):
        with self.client.websocket_connect(f"/ws/admin?token={self.admin_token}") as ws:
            # 1. First message should be the 'init' event containing state snapshots
            init_msg_raw = ws.receive_text()
            init_msg = json.loads(init_msg_raw)
            self.assertEqual(init_msg.get("event"), "init")
            self.assertIn("data", init_msg)
            self.assertIn("recent_metrics", init_msg["data"])

            # 2. Test ping-pong
            ws.send_text("ping")
            pong_raw = ws.receive_text()
            pong = json.loads(pong_raw)
            self.assertEqual(pong.get("event"), "pong")

            # 3. Test live event broadcast
            ws_manager.broadcast_sync("test_alert", {"msg": "hello from test"})
            event_raw = ws.receive_text()
            event = json.loads(event_raw)
            self.assertEqual(event.get("event"), "test_alert")
            self.assertEqual(event.get("data", {}).get("msg"), "hello from test")


if __name__ == "__main__":
    unittest.main()
