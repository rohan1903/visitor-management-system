import json
import os
import sys
import importlib.util
import unittest
from pathlib import Path
from datetime import datetime, timedelta


def load_gate_app_module():
    """
    Load gate/app.py as a uniquely-named module to avoid name collisions with other Flask apps.
    """
    gate_dir = Path(__file__).resolve().parents[1]
    app_path = gate_dir / "app.py"

    # Ensure mock mode before module execution.
    os.environ["USE_MOCK_DATA"] = "True"
    os.environ["AUTH_MODE"] = os.environ.get("AUTH_MODE", "hybrid")
    # Avoid needing to sleep between check-in and check-out in edge-case tests.
    os.environ["CHECKIN_COOLDOWN_SECONDS"] = os.environ.get("CHECKIN_COOLDOWN_SECONDS", "0")

    # gate/app.py uses `from qr_module import ...` (non-package import),
    # so gate/ must be on sys.path for module execution to succeed.
    sys.path.insert(0, str(gate_dir))

    spec = importlib.util.spec_from_file_location("gate_app_mock_tests", str(app_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load spec for {app_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GateEdgeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = load_gate_app_module()
        cls.client = cls.gate.app.test_client()

    def setUp(self):
        # Reset in-memory DB state for each test.
        self.gate.db_ref = self.gate.InMemoryDBRef(self.gate.build_mock_gate_data())

    def _get_visit(self, visitor_id: str, visit_id: str):
        visit = self.gate.db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").get()
        self.assertIsNotNone(visit, f"Missing visit {visitor_id}/{visit_id}")
        return visit

    def _post_mock_auth(self, mock_face_id: str, qr_data: str | None):
        payload = {"mock_face_id": mock_face_id}
        if qr_data is not None:
            payload["qr_data"] = qr_data
        resp = self.client.post("/mock_auth", json=payload)
        self.assertEqual(resp.status_code, 200)
        return resp.get_json() or {}

    def test_right_face_wrong_qr_owner_invalidates_qr(self):
        v1 = "visitor_demo_1"
        v2 = "visitor_demo_2"
        visit_id = "visit_demo_1"
        qr_payload = self._get_visit(v1, visit_id)["qr_payload"]

        res = self._post_mock_auth(mock_face_id=v2, qr_data=qr_payload)
        self.assertEqual(res.get("status"), "denied")
        self.assertIn("Security alert", res.get("message", ""))

        qr_state = self._get_visit(v1, visit_id).get("qr_state", {})
        self.assertEqual(qr_state.get("status"), self.gate.QR_INVALIDATED)

    def test_stolen_qr_invalidated_on_face_only_checkout(self):
        v1 = "visitor_demo_1"
        visit_id = "visit_demo_1"
        qr_payload = self._get_visit(v1, visit_id)["qr_payload"]

        # Check-in with QR.
        res1 = self._post_mock_auth(mock_face_id=v1, qr_data=qr_payload)
        self.assertEqual(res1.get("status"), "granted")
        self.assertIn("Successful check-in", res1.get("message", ""))

        # Checkout without QR (face-only).
        res2 = self._post_mock_auth(mock_face_id=v1, qr_data=None)
        self.assertEqual(res2.get("status"), "checked_out")
        self.assertIn("QR invalidated", res2.get("message", ""))

        qr_state = self._get_visit(v1, visit_id).get("qr_state", {})
        self.assertEqual(qr_state.get("status"), self.gate.QR_INVALIDATED)
        self.assertIn("possible lost", qr_state.get("invalidated_reason", ""))

    def test_qr_replay_denied_after_checkout_used(self):
        v1 = "visitor_demo_1"
        visit_id = "visit_demo_1"
        qr_payload = self._get_visit(v1, visit_id)["qr_payload"]

        # Check-in (QR).
        res1 = self._post_mock_auth(mock_face_id=v1, qr_data=qr_payload)
        self.assertEqual(res1.get("status"), "granted")

        # Advance QR scan time so the next scan isn't blocked by QR_SCAN_COOLDOWN_SECONDS.
        past_str = (datetime.now() - timedelta(seconds=61)).strftime("%Y-%m-%d %H:%M:%S")
        self.gate.db_ref.child(f"visitors/{v1}/visits/{visit_id}/qr_state").update(
            {"checkin_scan_time": past_str}
        )

        # Check-out (QR again).
        res2 = self._post_mock_auth(mock_face_id=v1, qr_data=qr_payload)
        self.assertEqual(res2.get("status"), "checked_out")

        # Replay attempt (QR a third time) must fail QR validation.
        res3 = self._post_mock_auth(mock_face_id=v1, qr_data=qr_payload)
        self.assertEqual(res3.get("status"), "denied")
        self.assertIn("QR invalid:", res3.get("message", ""))

    def test_expired_qr_denied(self):
        v1 = "visitor_demo_1"
        visit_id = "visit_demo_1"
        visit = self._get_visit(v1, visit_id)
        token = visit.get("qr_token")
        self.assertTrue(token, "Missing stored qr_token in mock data")

        expired_payload = json.dumps(
            {"v": v1, "i": visit_id, "k": token, "e": "2000-01-01 00:00:00"},
            separators=(",", ":"),
        )

        res = self._post_mock_auth(mock_face_id=v1, qr_data=expired_payload)
        self.assertEqual(res.get("status"), "denied")
        self.assertIn("QR invalid:", res.get("message", ""))

    def test_blacklisted_visitor_denied_and_qr_invalidated(self):
        v1 = "visitor_demo_1"
        visit_id = "visit_demo_1"
        qr_payload = self._get_visit(v1, visit_id)["qr_payload"]

        # Blacklist the visitor in the mock DB.
        self.gate.db_ref.child(f"visitors/{v1}/basic_info").update({"blacklisted": "yes"})

        res = self._post_mock_auth(mock_face_id=v1, qr_data=qr_payload)
        self.assertEqual(res.get("status"), "denied")
        self.assertIn("blacklisted", res.get("message", "").lower())

        qr_state = self._get_visit(v1, visit_id).get("qr_state", {})
        self.assertEqual(qr_state.get("status"), self.gate.QR_INVALIDATED)

    def test_feedback_form_validation(self):
        # Missing visitor_id -> 400
        resp1 = self.client.get("/feedback_form")
        self.assertEqual(resp1.status_code, 400)

        # Invalid visitor_id -> 404
        resp2 = self.client.get("/feedback_form?visitor_id=does_not_exist")
        self.assertEqual(resp2.status_code, 404)

        # Empty feedback -> rendered form with 200 OK (template), but should include error text.
        resp3 = self.client.post(
            "/submit_feedback",
            data={"visitor_id": "visitor_demo_1", "feedback_text": ""},
        )
        self.assertEqual(resp3.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)

