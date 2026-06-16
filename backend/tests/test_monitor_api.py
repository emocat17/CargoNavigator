"""Integration tests for monitor and archive API endpoints."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestMonitorStart:
    def test_rejects_nonexistent_order(self):
        r = client.post("/api/v1/monitor/start/nonexistent-id")
        assert r.status_code == 400
        assert "不存在" in r.json()["detail"]

    def test_rejects_draft_order(self):
        r = client.post("/api/v1/tracking/orders", json={
            "application_id": None,
            "route_data": {"path_points": "119.0,26.0;119.1,26.1"},
            "vehicle_info": {},
            "assessment_data": {},
        })
        assert r.status_code == 201
        order_id = r.json()["data"]["id"]

        r2 = client.post(f"/api/v1/monitor/start/{order_id}")
        assert r2.status_code == 400
        assert "已发证" in r2.json()["detail"]

    def test_rejects_no_polyline(self):
        r = client.post("/api/v1/tracking/orders", json={
            "route_data": {}, "vehicle_info": {}, "assessment_data": {},
        })
        assert r.status_code == 201
        order_id = r.json()["data"]["id"]

        for status in ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "PERMIT_ISSUED"]:
            client.put(f"/api/v1/tracking/orders/{order_id}/status",
                       json={"new_status": status})

        r2 = client.post(f"/api/v1/monitor/start/{order_id}")
        assert r2.status_code == 400
        assert "polyline" in r2.json()["detail"]


class TestArchive:
    def test_archive_404(self):
        r = client.get("/api/v1/archive/nonexistent-id")
        assert r.status_code == 404

    def test_export_404(self):
        r = client.get("/api/v1/archive/nonexistent-id/export?format=json")
        assert r.status_code == 404


class TestSessions:
    def test_list_empty(self):
        r = client.get("/api/v1/monitor/sessions")
        assert r.status_code == 200
        assert r.json()["code"] == 200
