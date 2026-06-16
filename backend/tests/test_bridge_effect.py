"""
Tests for app.services.bridge_effect_calculator.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bridge_effect_calculator import (
    calc_damping_factor,
    _parse_station_k,
    calculate_bridge_effect,
)
from app.bridge_db import query, query_one


# ============================================================================
# calc_damping_factor
# ============================================================================

class TestCalcDampingFactor:
    """Impact coefficient μ based on bridge natural frequency."""

    def test_below_1_5_hz(self):
        """f < 1.5 Hz → μ = 0.05"""
        assert calc_damping_factor(0.5) == 0.05
        assert calc_damping_factor(1.0) == 0.05
        assert calc_damping_factor(1.49) == 0.05

    def test_between_1_5_and_14_hz(self):
        """1.5 ≤ f ≤ 14 Hz → μ = 0.1767·ln(f) - 0.0157"""
        import math
        f = 5.0
        expected = 0.1767 * math.log(f) - 0.0157
        assert abs(calc_damping_factor(f) - expected) < 1e-10

        # Boundary at 1.5
        expected_1_5 = 0.1767 * math.log(1.5) - 0.0157
        assert abs(calc_damping_factor(1.5) - expected_1_5) < 1e-10

        # Boundary at 14
        expected_14 = 0.1767 * math.log(14) - 0.0157
        assert abs(calc_damping_factor(14) - expected_14) < 1e-10

    def test_above_14_hz(self):
        """f > 14 Hz → μ = 0.45"""
        assert calc_damping_factor(15) == 0.45
        assert calc_damping_factor(100) == 0.45


# ============================================================================
# _parse_station_k
# ============================================================================

class TestParseStationK:
    """Parse station桩号 strings to K (km) values."""

    @pytest.mark.parametrize("station, expected", [
        ("k0+15", 0.015),
        ("k1074", 1074.0),
        ("k36+19", 36.019),
        ("K0+15", 0.015),
        ("k0+0", 0.0),
        ("k1+500", 1.5),
        ("K100+999", 100.999),
        ("k2338", 2338.0),
        ("k28+600", 28.6),
    ])
    def test_valid_formats(self, station, expected):
        assert _parse_station_k(station) == pytest.approx(expected, abs=0.001)

    def test_empty_string(self):
        assert _parse_station_k("") is None

    def test_invalid_formats(self):
        assert _parse_station_k("abc") is None
        assert _parse_station_k("K") is None
        assert _parse_station_k("123") is None
        assert _parse_station_k("NK0+15") is None
        assert _parse_station_k("kabc") is None

    def test_case_insensitive(self):
        """Upper/lower case K should both work."""
        assert _parse_station_k("K0+15") == pytest.approx(0.015, abs=0.001)
        assert _parse_station_k("k0+15") == pytest.approx(0.015, abs=0.001)

    def test_spaces_ignored(self):
        assert _parse_station_k("k0 + 15") == pytest.approx(0.015, abs=0.001)
        assert _parse_station_k(" K0+15 ") == pytest.approx(0.015, abs=0.001)


# ============================================================================
# calculate_bridge_effect
# ============================================================================

class TestCalculateBridgeEffect:
    """Integration tests that require the real SQLite bridge DB."""

    @pytest.fixture(autouse=True)
    def _check_db(self):
        """Skip all tests in this class if the DB is missing."""
        db_path = Path(__file__).parent.parent / "data" / "cargo_bridge.db"
        if not db_path.exists():
            pytest.skip("Bridge database not found")

    def test_valid_station_returns_expected_keys(self):
        """Query a real bridge from the DB and calculate effect for it."""
        # Find any bridge that has influence line data
        bridges = query(
            """SELECT b.*
               FROM bridges b
               JOIN bridge_influence_lines il ON b.id = il.bridge_id
               GROUP BY b.id
               LIMIT 1"""
        )
        assert bridges, "No bridges with influence data found in DB"
        bridge = bridges[0]

        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station=bridge["station"],
            highway_code=bridge["highway_code"],
        )

        # Should not be an error
        assert "error" not in result, f"Got error: {result.get('error')}"

        # Check all expected keys are present
        expected_keys = [
            "station", "bridge_type", "highway_code", "damping_factor",
            "pos_moment_ratio", "neg_moment_ratio", "shear_ratio",
            "pos_moment_effect", "neg_moment_effect", "shear_effect",
            "is_passable",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

        # Type checks
        assert isinstance(result["station"], str)
        assert isinstance(result["damping_factor"], float)
        assert isinstance(result["is_passable"], bool)
        assert isinstance(result["pos_moment_effect"], list)
        assert len(result["pos_moment_effect"]) == 2

    def test_invalid_station_returns_error(self):
        """Non-existent station should return error dict."""
        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station="k99999",
        )
        assert "error" in result
        assert "k99999" in result["error"]

    def test_invalid_station_with_highway_code(self):
        """Non-existent station with highway code should also error."""
        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station="k99999",
            highway_code="G99",
        )
        assert "error" in result

    def test_damping_factor_in_result(self):
        """Verify damping factor is present and calculated."""
        bridges = query(
            """SELECT b.*
               FROM bridges b
               JOIN bridge_influence_lines il ON b.id = il.bridge_id
               GROUP BY b.id
               LIMIT 1"""
        )
        if not bridges:
            pytest.skip("No bridges with influence data")
        bridge = bridges[0]

        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station=bridge["station"],
            highway_code=bridge["highway_code"],
        )

        assert "error" not in result
        # damping_factor should be a float > 0
        assert result["damping_factor"] > 0
        # For the bridge we saw (freq=2.39), damping should be between 0.05 and 0.45
        assert 0.05 <= result["damping_factor"] <= 0.45

    def test_ratio_strings_are_well_formed(self):
        """Ratio strings should be formatted like '0.xxxx~0.xxxx'."""
        bridges = query(
            """SELECT b.*
               FROM bridges b
               JOIN bridge_influence_lines il ON b.id = il.bridge_id
               GROUP BY b.id
               LIMIT 1"""
        )
        if not bridges:
            pytest.skip("No bridges with influence data")
        bridge = bridges[0]

        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station=bridge["station"],
            highway_code=bridge["highway_code"],
        )

        import re
        ratio_pattern = re.compile(r'^-?\d+\.\d{4}~-?\d+\.\d{4}$')
        assert ratio_pattern.match(result["pos_moment_ratio"]), result["pos_moment_ratio"]
        assert ratio_pattern.match(result["neg_moment_ratio"]), result["neg_moment_ratio"]
        assert ratio_pattern.match(result["shear_ratio"]), result["shear_ratio"]


# ============================================================================
# get_passability_grade
# ============================================================================

class TestGetPassabilityGrade:
    """Test the graduated passability grade mapping."""

    @pytest.mark.parametrize("ratio, expected_grade, expected_speed, expected_lane, expected_escort, expected_reinforce", [
        # < 0.6 → 安全通行
        (0.0, "安全通行", None, "all_lanes", False, False),
        (0.3, "安全通行", None, "all_lanes", False, False),
        (0.5999, "安全通行", None, "all_lanes", False, False),
        # 0.6 - 0.8 → 正常通行
        (0.6, "正常通行", None, "all_lanes", False, False),
        (0.7, "正常通行", None, "all_lanes", False, False),
        (0.7999, "正常通行", None, "all_lanes", False, False),
        # 0.8 - 0.9 → 建议限速
        (0.8, "建议限速", 40, "single_lane", False, False),
        (0.85, "建议限速", 40, "single_lane", False, False),
        (0.8999, "建议限速", 40, "single_lane", False, False),
        # 0.9 - 1.0 → 限速通行
        (0.9, "限速通行", 30, "center_only", False, False),
        (0.95, "限速通行", 30, "center_only", False, False),
        (0.9999, "限速通行", 30, "center_only", False, False),
        # 1.0 - 1.1 → 条件通行
        (1.0, "条件通行", 20, "center_only", True, False),
        (1.05, "条件通行", 20, "center_only", True, False),
        (1.0999, "条件通行", 20, "center_only", True, False),
        # 1.1 - 1.2 → 谨慎通行
        (1.1, "谨慎通行", 10, "center_only", True, True),
        (1.15, "谨慎通行", 10, "center_only", True, True),
        (1.1999, "谨慎通行", 10, "center_only", True, True),
        # >= 1.2 → 不建议通行
        (1.2, "不建议通行", 0, "none", True, True),
        (1.5, "不建议通行", 0, "none", True, True),
        (5.0, "不建议通行", 0, "none", True, True),
    ])
    def test_ratio_thresholds(self, ratio, expected_grade, expected_speed, expected_lane, expected_escort, expected_reinforce):
        """Each ratio threshold maps to the correct grade and restrictions."""
        from app.services.bridge_effect_calculator import get_passability_grade

        result = get_passability_grade(ratio)

        assert result["grade"] == expected_grade, f"ratio={ratio}: expected grade={expected_grade}, got {result['grade']}"
        assert result["max_speed_kmh"] == expected_speed, f"ratio={ratio}: wrong speed"
        assert result["lane_restriction"] == expected_lane, f"ratio={ratio}: wrong lane"
        assert result["escort_required"] == expected_escort, f"ratio={ratio}: wrong escort"
        assert result["reinforcement_needed"] == expected_reinforce, f"ratio={ratio}: wrong reinforce"

    def test_result_structure(self):
        """Result dict has all expected keys."""
        from app.services.bridge_effect_calculator import get_passability_grade

        result = get_passability_grade(0.5)

        expected_keys = [
            "grade", "max_speed_kmh", "lane_restriction",
            "escort_required", "reinforcement_needed", "bridge_specific_notes",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_negative_ratio(self):
        """Negative ratios should map to 安全通行 (treated like < 0.6)."""
        from app.services.bridge_effect_calculator import get_passability_grade

        result = get_passability_grade(-0.1)
        assert result["grade"] == "安全通行"
        assert result["lane_restriction"] == "all_lanes"
        assert not result["reinforcement_needed"]


class TestCalculateBridgeEffectPassability:
    """Verify passability is included in calculate_bridge_effect results."""

    @pytest.fixture(autouse=True)
    def _check_db(self):
        """Skip all tests in this class if the DB is missing."""
        db_path = Path(__file__).parent.parent / "data" / "cargo_bridge.db"
        if not db_path.exists():
            pytest.skip("Bridge database not found")

    def test_result_includes_passability(self):
        """calculate_bridge_effect should include the passability dict."""
        from app.services.bridge_effect_calculator import calculate_bridge_effect

        bridges = query(
            """SELECT b.*
               FROM bridges b
               JOIN bridge_influence_lines il ON b.id = il.bridge_id
               GROUP BY b.id
               LIMIT 1"""
        )
        assert bridges, "No bridges with influence data found in DB"
        bridge = bridges[0]

        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station=bridge["station"],
            highway_code=bridge["highway_code"],
        )

        assert "error" not in result, f"Got error: {result.get('error')}"

        # New passability key must be present
        assert "passability" in result, "Missing 'passability' key"
        passability = result["passability"]

        # Check passability structure
        assert "grade" in passability
        assert "max_speed_kmh" in passability
        assert "lane_restriction" in passability
        assert "escort_required" in passability
        assert "reinforcement_needed" in passability
        assert "bridge_specific_notes" in passability

        # Backward compatibility: is_passable should still exist
        assert "is_passable" in result
        assert isinstance(result["is_passable"], bool)

        # is_passable and passability.grade should be consistent
        # ratio < 1.0 should correspond to is_passable=True
        if result["max_ratio"] < 1.0:
            assert result["is_passable"] is True
        else:
            assert result["is_passable"] is False

    def test_passability_grade_matches_ratio(self):
        """The passability grade should match the max_ratio."""
        from app.services.bridge_effect_calculator import calculate_bridge_effect, get_passability_grade

        bridges = query(
            """SELECT b.*
               FROM bridges b
               JOIN bridge_influence_lines il ON b.id = il.bridge_id
               GROUP BY b.id
               LIMIT 1"""
        )
        if not bridges:
            pytest.skip("No bridges with influence data")
        bridge = bridges[0]

        result = calculate_bridge_effect(
            loads_ton=[10, 15, 12],
            spacings=[3.5, 1.2],
            station=bridge["station"],
            highway_code=bridge["highway_code"],
        )

        if "error" in result:
            pytest.skip(f"Calculation error: {result['error']}")

        # The passability in result should match what get_passability_grade produces
        expected = get_passability_grade(result["max_ratio"])
        actual = result["passability"]

        assert actual["grade"] == expected["grade"], \
            f"Grade mismatch: expected {expected['grade']}, got {actual['grade']}"
        assert actual["max_speed_kmh"] == expected["max_speed_kmh"]
        assert actual["lane_restriction"] == expected["lane_restriction"]
        assert actual["escort_required"] == expected["escort_required"]
        assert actual["reinforcement_needed"] == expected["reinforcement_needed"]
