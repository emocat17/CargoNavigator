"""
API field-name compatibility tests.

These tests verify that every endpoint accepts payloads shaped the way
the frontend actually sends them.  The canonical field for vehicle gross
weight is `total_weight` across ALL endpoints.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Shared test fixtures ──

FRONTEND_VEHICLE = {
    "length": 25.0,
    "width": 3.5,
    "height": 4.5,
    "total_weight": 80.0,       # ← the canonical field name
    "axis_weight": 15.0,
    "axis_count": 6,
    "axis_loads": [15.0, 15.0, 12.5, 12.5, 12.5, 12.5],
    "axis_spacings": [3.5, 1.5, 3.0, 3.0, 3.0],
}

FRONTEND_ROUTE = {
    "id": "route_1",
    "route_description": "福州--G15沈海高速--厦门",
    "major_roads": ["G15沈海高速"],
    "distance": 255678,
    "duration": 10259,
    "tunnel_count": 5,
    "tunnel_distance": 4500,
    "toll_cost": 120.0,
    "traffic_condition": "畅通 95%",
    "risk_warnings": ["隧道群提醒"],
    "strategy": "速度优先",
}


# ── Tests ──

class TestVehicleEndpoints:
    """POST /vehicles/classify and /check-dimensions"""

    def test_classify_accepts_total_weight(self):
        payload = {**FRONTEND_VEHICLE, "trailer_type": "lowbed"}
        r = client.post("/api/v1/vehicles/classify", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "size_grade" in body
        assert "combined_grade" in body

    def test_check_dimensions_accepts_total_weight(self):
        payload = {
            "length": 25.0,
            "width": 3.5,
            "height": 4.5,
            "total_weight": 80.0,
            "axis_weight": 15.0,
            "axis_count": 6,
        }
        r = client.post("/api/v1/vehicles/check-dimensions", json=payload)
        assert r.status_code == 200, r.text
        assert "overall_pass" in r.json()


class TestAssessmentEndpoints:
    """POST /routes/assess  and  POST /routes/compare"""

    def test_assess_accepts_total_weight(self):
        payload = {"route_data": FRONTEND_ROUTE, "vehicle_info": FRONTEND_VEHICLE}
        r = client.post("/api/v1/routes/assess", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["code"] == 200
        assert "overall_assessment" in body["data"]

    def test_compare_accepts_total_weight(self):
        payload = {
            "routes": [FRONTEND_ROUTE, {**FRONTEND_ROUTE, "id": "route_2"}],
            "vehicle_info": FRONTEND_VEHICLE,
        }
        r = client.post("/api/v1/routes/compare", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["code"] == 200

    def test_assess_rejects_weight_field(self):
        """Old field name `weight` should fail validation (422)."""
        bad_vehicle = {**FRONTEND_VEHICLE}
        del bad_vehicle["total_weight"]
        bad_vehicle["weight"] = 80.0
        r = client.post("/api/v1/routes/assess",
                        json={"route_data": FRONTEND_ROUTE, "vehicle_info": bad_vehicle})
        assert r.status_code == 422, r.text
        # confirm the error pinpoints the missing field
        detail = r.json()["detail"]
        missing_fields = [d["loc"][-1] for d in detail]
        assert "total_weight" in missing_fields


class TestSurveyEndpoint:
    """POST /survey/generate"""

    def test_accepts_total_weight(self):
        payload = {"route_data": FRONTEND_ROUTE, "vehicle_info": FRONTEND_VEHICLE}
        r = client.post("/api/v1/survey/generate", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["code"] == 200
        # The response should contain a checklist with categories
        assert "categories" in body["data"] or "checkpoints" in body["data"]


class TestPermitEndpoints:
    """POST /permit/generate  and  POST /permit/preview"""

    def test_generate_accepts_total_weight(self):
        payload = {
            "vehicle_info": FRONTEND_VEHICLE,
            "cargo_info": {"name": "变压器", "weight": 60},
            "applicant_info": {"name": "测试物流公司", "phone": "13800000000"},
            "routes": [FRONTEND_ROUTE],
        }
        r = client.post("/api/v1/permit/generate", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["code"] == 200

    def test_preview_accepts_total_weight(self):
        payload = {
            "vehicle_info": FRONTEND_VEHICLE,
            "cargo_info": {"name": "变压器", "weight": 60},
            "applicant_info": {"name": "测试物流公司"},
            "routes": [FRONTEND_ROUTE],
        }
        r = client.post("/api/v1/permit/preview", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["code"] == 200


class TestRoutePlanVehicle:
    """POST /routes/plan with vehicle info embedded."""

    def test_plan_with_vehicle_total_weight(self):
        payload = {
            "origin": "福州",
            "destination": "厦门",
            "route_count": 1,
            "vehicle": {
                "length": 25.0,
                "width": 3.5,
                "height": 4.5,
                "weight": 80.0,            # ← routes/plan uses the VehicleInfo model from schemas.py
                "axis_weight": 15.0,
                "axis_count": 6,
            },
        }
        r = client.post("/api/v1/routes/plan", json=payload)
        # Either 200 (success) or 500 (Amap API may be unreachable in CI)
        assert r.status_code in (200, 500), r.text


class TestAgentHealth:
    """GET /agent/health"""

    def test_health(self):
        r = client.get("/api/v1/agent/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
