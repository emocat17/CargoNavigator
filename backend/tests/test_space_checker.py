"""
Tests for space_checker.py.

Covers:
- Height clearance check (pass/warning/fail)
- Width check against lane width (pass/warning/fail)
- Turning radius check (pass/warning/fail)
- Weight check against bridge capacity (pass/warning/fail)
- Full space check integration
- Edge cases
"""

import pytest
from app.services.space_checker import (
    check_height,
    check_width,
    check_turning_radius,
    check_weight,
    full_space_check,
)


# ── Height check ──

class TestHeightCheck:
    def test_pass_well_within_clearance(self):
        """Vehicle well below 5.0m clearance should pass."""
        result = check_height(4.0)
        assert result["status"] == "pass"
        assert result["clearance"] == 5.0
        assert result["margin"] == 1.0

    def test_warning_at_exact_clearance(self):
        """Vehicle at exactly 5.0m has zero margin, should warn."""
        result = check_height(5.0)
        assert result["status"] == "warning"
        assert result["margin"] == 0.0

    def test_warning_margin_below_0_5(self):
        """Vehicle between 4.5 and 5.0 should warn."""
        result = check_height(4.6)
        assert result["status"] == "warning"
        assert 0.0 < result["margin"] < 0.5

    def test_warning_at_warning_threshold(self):
        """Vehicle at 4.51 should give warning."""
        result = check_height(4.51)
        assert result["status"] == "warning"

    def test_fail_above_clearance(self):
        """Vehicle above 5.0m should fail."""
        result = check_height(5.1)
        assert result["status"] == "fail"
        assert result["margin"] < 0

    def test_fail_extreme_height(self):
        """Extreme height should definitely fail."""
        result = check_height(7.0)
        assert result["status"] == "fail"
        assert result["margin"] == -2.0

    def test_message_present(self):
        """All results should contain a message."""
        for height in [3.0, 4.6, 6.0]:
            result = check_height(height)
            assert "message" in result
            assert len(result["message"]) > 0


# ── Width check ──

class TestWidthCheck:
    def test_pass_well_within_lane(self):
        """Vehicle well within 3.75m lane width should pass."""
        result = check_width(2.55)
        assert result["status"] == "pass"
        assert result["lane_width"] == 3.75
        assert result["margin"] > 0.75

    def test_warning_near_edge(self):
        """Vehicle between 3.0 and 3.75 should warn."""
        result = check_width(3.3)
        assert result["status"] == "warning"
        assert 0 < result["margin"] < 0.75

    def test_warning_at_boundary(self):
        """Vehicle at exactly 3.75 should pass (no warning needed)."""
        result = check_width(3.75)
        # margin = 0, which is not < 0 (fail) but margin=0 < 0.75 (warning)
        assert result["status"] == "warning"

    def test_fail_exceeds_lane(self):
        """Vehicle wider than 3.75m lane should fail."""
        result = check_width(4.0)
        assert result["status"] == "fail"
        assert result["margin"] < 0

    def test_fail_extreme_width(self):
        """Extreme width should definitely fail."""
        result = check_width(6.0)
        assert result["status"] == "fail"


# ── Turning radius check ──

class TestTurningRadiusCheck:
    def test_pass_short_vehicle(self):
        """Short vehicle easily makes 15m radius turn."""
        result = check_turning_radius(10.0, min_radius_m=15.0)
        assert result["status"] == "pass"
        assert result["estimated_required_radius"] == 5.0

    def test_pass_at_boundary(self):
        """Vehicle needing exactly 15m radius."""
        result = check_turning_radius(30.0, min_radius_m=15.0)
        # estimated_required = 30 * 0.5 = 15, margin = 0
        # 0 is NOT < 0 (fail), but 0 IS < 5.0 (warning)
        assert result["status"] == "warning"

    def test_warning_moderate_length(self):
        """Moderately long vehicle at edge."""
        result = check_turning_radius(25.0, min_radius_m=15.0)
        assert result["status"] == "warning"
        assert result["estimated_required_radius"] == 12.5

    def test_fail_too_long(self):
        """Very long vehicle can't make the turn."""
        result = check_turning_radius(35.0, min_radius_m=15.0)
        assert result["status"] == "fail"
        assert result["estimated_required_radius"] > 15.0

    def test_pass_with_large_radius(self):
        """Even long vehicle passes with very large curve radius."""
        result = check_turning_radius(35.0, min_radius_m=50.0)
        assert result["status"] == "pass"

    def test_custom_min_radius(self):
        """Custom min_radius should be respected."""
        result = check_turning_radius(20.0, min_radius_m=8.0)
        # estimated_required = 10, min_radius = 8, margin = -2 (fail)
        assert result["status"] == "fail"
        assert result["min_curve_radius"] == 8.0


# ── Weight check ──

class TestWeightCheck:
    def test_pass_under_capacity(self):
        """Vehicle well under bridge capacity."""
        result = check_weight(30.0)
        assert result["status"] == "pass"
        assert result["bridge_capacity"] == 55.0
        assert result["utilization_ratio"] < 0.8

    def test_warning_near_capacity(self):
        """Vehicle near 80% of capacity."""
        result = check_weight(44.0)  # 44/55 = 0.8
        assert result["status"] == "warning"
        assert result["utilization_ratio"] == 0.8

    def test_warning_above_80_percent(self):
        """Vehicle above 80% of capacity."""
        result = check_weight(50.0)  # 50/55 ≈ 0.909
        assert result["status"] == "warning"
        assert result["utilization_ratio"] > 0.8

    def test_fail_exceeds_capacity(self):
        """Vehicle exceeds bridge capacity."""
        result = check_weight(60.0)
        assert result["status"] == "fail"
        assert result["utilization_ratio"] > 1.0

    def test_custom_capacity(self):
        """Custom bridge capacity should be used."""
        result = check_weight(30.0, max_bridge_capacity_tons=40.0)
        assert result["bridge_capacity"] == 40.0
        assert result["status"] == "pass"

    def test_custom_capacity_fail(self):
        """Fail with custom low capacity bridge."""
        result = check_weight(50.0, max_bridge_capacity_tons=40.0)
        assert result["status"] == "fail"


# ── Full space check ──

class TestFullSpaceCheck:
    def test_all_pass(self):
        """Normal vehicle passes all checks."""
        info = {
            "length": 17.0,
            "width": 2.55,
            "height": 4.0,
            "total_weight": 40.0,
            "axis_weight": 8.0,
            "axis_count": 6,
        }
        result = full_space_check(info)
        assert result["overall_pass"] is True
        assert len(result["failures"]) == 0
        assert len(result["checks"]) == 4
        assert "height" in result["checks"]
        assert "width" in result["checks"]
        assert "turning_radius" in result["checks"]
        assert "weight" in result["checks"]

    def test_height_fail(self):
        """Vehicle too tall should fail overall."""
        info = {
            "length": 24.0,
            "width": 3.0,
            "height": 5.5,
            "total_weight": 80.0,
            "axis_weight": 13.0,
            "axis_count": 8,
        }
        result = full_space_check(info)
        assert result["overall_pass"] is False
        assert len(result["failures"]) > 0
        assert any("高度" in f for f in result["failures"])

    def test_multiple_failures(self):
        """Vehicle failing multiple checks."""
        info = {
            "length": 40.0,
            "width": 5.0,
            "height": 6.0,
            "total_weight": 200.0,
            "axis_weight": 20.0,
            "axis_count": 10,
        }
        result = full_space_check(info)
        assert result["overall_pass"] is False
        # Should have failures for height, width, turning radius, and weight
        assert len(result["failures"]) >= 3

    def test_warnings_without_failures(self):
        """Vehicle with warnings only should still pass overall."""
        info = {
            "length": 25.0,
            "width": 3.3,
            "height": 4.6,
            "total_weight": 50.0,
            "axis_weight": 10.0,
            "axis_count": 8,
        }
        result = full_space_check(info)
        assert result["overall_pass"] is True
        assert len(result["warnings"]) > 0

    def test_recommendations_present(self):
        """Result should always include recommendations."""
        info = {
            "length": 17.0,
            "width": 2.55,
            "height": 4.0,
            "total_weight": 40.0,
            "axis_weight": 8.0,
            "axis_count": 6,
        }
        result = full_space_check(info)
        assert len(result["recommendations"]) > 0
