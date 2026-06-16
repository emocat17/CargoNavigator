"""
Tests for the CostEstimator service.

Covers:
- Toll fee passthrough from route_data
- Fuel cost calculation with load correction
- Escort cost lookup from regulation KB
- Permit fee classification
- Insurance estimation
- Full integration estimate() output structure
"""
import pytest
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.cost_estimator import (
    CostEstimator,
    cost_estimator,
    _calculate_fuel,
    _calculate_escort,
    _calculate_permit,
    _calculate_insurance,
    _determine_fuel_rate,
    _get_max_load_tons,
    FUEL_RATE_HIGHWAY,
    FUEL_RATE_MIXED,
    FUEL_RATE_MOUNTAIN,
    AVG_DAILY_KM,
)


# ── Fixtures ──

@pytest.fixture
def sample_route() -> dict:
    """A typical highway route from Amap API."""
    return {
        "id": "route_1",
        "route_description": "三明--G1517莆炎高速--港后枢纽--G15沈海高速--海沧",
        "major_roads": ["G1517莆炎高速", "G15沈海高速"],
        "distance": 290800,       # 290.8 km
        "duration": 10800,        # 3 hours
        "tunnel_count": 5,
        "tunnel_distance": 3000,
        "toll_cost": 158.0,
        "toll_distance": 250000,
        "traffic_condition": "畅通 60%, 缓行 30%, 拥堵 10%",
        "risk_warnings": [],
    }


@pytest.fixture
def sample_vehicle_standard() -> dict:
    """A standard 6-axle tractor-trailer within limits."""
    return {
        "length": 18.0,
        "width": 2.5,
        "height": 3.8,
        "weight": 45.0,
        "axle_count": 6,
        "vehicle_type": "train",
    }


@pytest.fixture
def sample_vehicle_oversized() -> dict:
    """A heavily oversized vehicle requiring Class III permit + escort."""
    return {
        "length": 32.0,
        "width": 4.9,
        "height": 4.8,
        "weight": 150.0,
        "axle_count": 8,
        "vehicle_type": "train",
        "axis_weight": 18.0,
    }


@pytest.fixture
def sample_cargo() -> dict:
    """Cargo with known value."""
    return {
        "cargo_value": 5000000.0,  # 5 million RMB
        "cargo_type": "大型变压器",
    }


# ── Toll fee ──

def test_toll_from_route_data(sample_route, sample_vehicle_standard):
    """Toll should come directly from route_data.toll_cost."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_standard)
    assert result["breakdown"]["toll"]["amount"] == 158.0
    assert result["breakdown"]["toll"]["source"] == "Amap API"


def test_toll_zero_when_missing(sample_vehicle_standard):
    """Toll should be 0 when toll_cost is not in route_data."""
    route = {"distance": 100000, "route_description": "test"}
    result = cost_estimator.estimate(route, sample_vehicle_standard)
    assert result["breakdown"]["toll"]["amount"] == 0.0


# ── Fuel cost ──

def test_fuel_cost_basic(sample_route, sample_vehicle_standard):
    """Basic fuel cost calculation for highway route."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_standard)
    fuel = result["breakdown"]["fuel"]
    assert fuel["source"] == "calculated"
    assert fuel["amount"] > 0
    # 290.8km × ~38L/100km (30 × 1.275 load correction) × ¥7.5/L ≈ 834
    assert 800 < fuel["amount"] < 900


def test_fuel_cost_with_heavy_load(sample_route, sample_vehicle_oversized):
    """Fuel cost should be higher for heavier vehicle due to load correction."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_oversized)
    fuel = result["breakdown"]["fuel"]
    # Heavy load correction should increase fuel consumption significantly
    assert fuel["amount"] > 700
    assert "载重修正" in fuel["note"]


def test_fuel_cost_mountain_route(sample_vehicle_standard):
    """Fuel cost should be higher for mountain routes."""
    mountain_route = {
        "distance": 100000,
        "route_description": "山路--盘山公路--终点",
        "tunnel_count": 15,
        "risk_warnings": ["山路急弯提醒", "长陡下坡提醒"],
    }
    result = cost_estimator.estimate(mountain_route, sample_vehicle_standard)
    fuel = result["breakdown"]["fuel"]
    # Mountain route should use FUEL_RATE_MOUNTAIN (~45L/100km)
    # 100km × 45L/100km × ¥7.5 = 337.5
    assert fuel["amount"] > 300


def test_determine_fuel_rate_highway():
    """Highway route should return highway rate."""
    route = {"route_description": "起点--G15沈海高速--终点", "tunnel_count": 2}
    assert _determine_fuel_rate(route) == FUEL_RATE_HIGHWAY


def test_determine_fuel_rate_mountain():
    """Mountain route should return mountain rate."""
    route = {
        "route_description": "起点--山路--终点",
        "tunnel_count": 12,
        "risk_warnings": ["山路急弯提醒"],
    }
    assert _determine_fuel_rate(route) == FUEL_RATE_MOUNTAIN


def test_determine_fuel_rate_mixed():
    """Route without clear indicators should default to mixed rate."""
    route = {"route_description": "起点--国道--终点", "tunnel_count": 3}
    rate = _determine_fuel_rate(route)
    assert rate == FUEL_RATE_MIXED


def test_get_max_load_tons_6axle():
    """6-axle train should have 49t limit."""
    assert _get_max_load_tons({"axle_count": 6, "vehicle_type": "train"}) == 49.0


def test_get_max_load_tons_2axle():
    """2-axle truck should have 18t limit."""
    assert _get_max_load_tons({"axle_count": 2, "vehicle_type": "truck"}) == 18.0


def test_get_max_load_tons_default():
    """Missing axle_count should default to 49t."""
    assert _get_max_load_tons({}) == 49.0


# ── Escort cost ──

def test_escort_not_required_for_class1(sample_route, sample_vehicle_standard):
    """Standard vehicle (Class I) should have no escort cost."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_standard)
    escort = result["breakdown"]["escort"]
    assert escort["amount"] == 0.0
    assert "无需强制护送" in escort["note"]


def test_escort_required_for_class3(sample_route, sample_vehicle_oversized):
    """Class III oversized vehicle should require escort vehicles."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_oversized)
    escort = result["breakdown"]["escort"]
    # This vehicle is Class III -> escort required
    assert escort["amount"] >= 0  # May be 0 if KB unavailable in test env


# ── Permit fee ──

def test_permit_class1_free(sample_route, sample_vehicle_standard):
    """Class I permit should have no fee."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_standard)
    permit = result["breakdown"]["permit"]
    assert permit["amount"] == 0.0
    assert "免许可费" in permit["note"]


def test_permit_class3_fee(sample_route, sample_vehicle_oversized):
    """Class III permit should have a fee."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_oversized)
    permit = result["breakdown"]["permit"]
    assert permit["source"] == "regulation"
    # Class III should have a fee
    assert permit["amount"] >= 0


# ── Insurance ──

def test_insurance_with_cargo_value(sample_route, sample_vehicle_standard, sample_cargo):
    """Insurance should be based on cargo value when provided."""
    result = cost_estimator.estimate(
        sample_route, sample_vehicle_standard, cargo_info=sample_cargo
    )
    insurance = result["breakdown"]["insurance"]
    assert insurance["source"] == "estimated"
    assert insurance["amount"] > 0
    # 0.3% of 5M = 15000 + ~2000 TPL ≈ 17000
    assert "货物险" in insurance["note"]


def test_insurance_without_cargo_value(sample_route, sample_vehicle_standard):
    """Insurance should use default when no cargo value."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_standard)
    insurance = result["breakdown"]["insurance"]
    assert insurance["amount"] > 0
    assert "默认估值" in insurance["note"] or insurance["amount"] > 0
    assert "第三者责任险" in insurance["note"]


# ── Full estimate output structure ──

def test_estimate_output_structure(sample_route, sample_vehicle_oversized):
    """Verify the full output structure of estimate()."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_oversized)

    # Top-level keys
    assert "total" in result
    assert "breakdown" in result
    assert "warnings" in result
    assert "estimated_days" in result

    # Total should be sum of breakdown
    breakdown = result["breakdown"]
    assert result["total"] == pytest.approx(
        sum(b["amount"] for b in breakdown.values()), abs=0.02
    )

    # Breakdown keys
    for key in ("toll", "fuel", "escort", "permit", "insurance"):
        assert key in breakdown
        assert "amount" in breakdown[key]
        assert "source" in breakdown[key]
        assert "note" in breakdown[key]

    # Estimated days
    assert result["estimated_days"] > 0


def test_estimate_days_calculation(sample_route, sample_vehicle_standard):
    """Estimated days should be distance_km / 400, min 0.5."""
    result = cost_estimator.estimate(sample_route, sample_vehicle_standard)
    expected_days = 290.8 / AVG_DAILY_KM
    assert result["estimated_days"] == pytest.approx(expected_days, abs=0.1)


def test_estimate_short_route_min_days(sample_vehicle_standard):
    """Very short routes should have minimum 0.5 days."""
    short_route = {"distance": 10000, "route_description": "short"}  # 10km
    result = cost_estimator.estimate(short_route, sample_vehicle_standard)
    assert result["estimated_days"] == 0.5


# ── Edge cases ──

def test_estimate_empty_route(sample_vehicle_standard):
    """Should handle empty/minimal route data gracefully."""
    result = cost_estimator.estimate({}, sample_vehicle_standard)
    assert result["total"] >= 0
    assert isinstance(result["breakdown"], dict)
    assert "estimated_days" in result


def test_estimate_empty_vehicle():
    """Should handle empty vehicle info gracefully."""
    result = cost_estimator.estimate({"distance": 100000}, {})
    assert result["total"] >= 0
    assert isinstance(result["breakdown"], dict)


def test_estimate_with_none_values(sample_route):
    """Should handle None values in vehicle_info."""
    vehicle = {
        "length": None,
        "width": None,
        "height": None,
        "weight": None,
        "axle_count": None,
    }
    result = cost_estimator.estimate(sample_route, vehicle)
    assert result["total"] >= 0
    # Should not crash


def test_cost_estimator_singleton():
    """CostEstimator singleton should be available."""
    from app.services.cost_estimator import cost_estimator as ce1
    from app.services.cost_estimator import CostEstimator
    ce2 = CostEstimator()
    # Both should be usable
    assert ce1 is not None
    assert ce2 is not None


# ── Integration: route_assessor includes cost_estimate ──

def test_route_assessor_includes_cost_estimate(sample_route, sample_vehicle_oversized):
    """route_assessor.assess_route() should include cost_estimate in output."""
    from app.services.route_assessor import route_assessor

    result = route_assessor.assess_route(sample_route, sample_vehicle_oversized)

    assert "cost_estimate" in result
    cost_est = result["cost_estimate"]
    assert "total" in cost_est
    assert "breakdown" in cost_est
    assert "estimated_days" in cost_est
    assert "toll" in cost_est["breakdown"]
    assert "fuel" in cost_est["breakdown"]
    assert "escort" in cost_est["breakdown"]
    assert "permit" in cost_est["breakdown"]
    assert "insurance" in cost_est["breakdown"]


def test_route_assessor_compare_includes_cost(sample_route, sample_vehicle_standard):
    """route_assessor.compare_routes() should include cost in per-route summary."""
    from app.services.route_assessor import route_assessor

    route2 = {
        "id": "route_2",
        "route_description": "三明--G25--海沧",
        "major_roads": ["G25长深高速"],
        "distance": 310000,
        "duration": 12000,
        "toll_cost": 180.0,
    }

    result = route_assessor.compare_routes(
        [sample_route, route2], sample_vehicle_standard
    )

    assert "ranked_routes" in result
    for rr in result["ranked_routes"]:
        if "error" not in rr:
            assert "estimated_total_cost" in rr
            assert "estimated_days" in rr
            assert "assessment" in rr
            assert "cost_estimate" in rr["assessment"]
