"""
Unit tests for Phase 12 (Admin Security Dashboard).

Tests:
1. Route availability: GET /admin/security-dashboard and GET /security-dashboard return 200 HTMLResponse.
2. Template rendering: HTML includes Chart.js, dashboard tables, and WebSocket hooks.
3. Static assets: static/js/security_dashboard.js and static/css/style.css are properly served.
"""

from pathlib import Path
import sys
import unittest

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fastapi.testclient import TestClient
from main import app


class TestSecurityDashboard(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_security_dashboard_routes_render_html(self):
        for path in ["/admin/security-dashboard", "/security-dashboard"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.headers["content-type"])
            content = resp.text

            # Check critical dashboard components
            self.assertIn("Honeypot & Security Telemetry", content)
            self.assertIn("sysMetricsChart", content)
            self.assertIn("rpsChart", content)
            self.assertIn("scoresTableBody", content)
            self.assertIn("trapSessionsTableBody", content)
            self.assertIn("blocksTableBody", content)
            self.assertIn("liveLogTableBody", content)
            self.assertIn("security_dashboard.js", content)
            self.assertIn("chart.js", content.lower())

    def test_static_assets_served(self):
        # JS asset
        js_resp = self.client.get("/static/js/security_dashboard.js")
        self.assertEqual(js_resp.status_code, 200)
        self.assertIn("Security & Honeypot Admin Dashboard", js_resp.text)

        # CSS asset
        css_resp = self.client.get("/static/css/style.css")
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn("SECURITY DASHBOARD (Phase 12)", css_resp.text)


if __name__ == "__main__":
    unittest.main()
