"""
Tests for vehicle_classifier.py.

Covers:
- Size classification boundaries (A-E)
- Axle load classification boundaries (A-E)
- Combined classification
- Edge cases (boundary values, trailer types)
"""

import pytest
from app.services.vehicle_classifier import (
    classify_size,
    classify_axle_load,
    classify_combined,
    _classify_width,
    _classify_length,
    _classify_height,
)


# ── Width classification ──

class TestWidthClassification:
    def test_width_grade_a_boundary(self):
        """Width <=3.0 is grade A, but >2.55 also A (oversized starts)."""
        assert _classify_width(2.55) == "A"
        assert _classify_width(2.6) == "A"
        assert _classify_width(3.0) == "A"

    def test_width_grade_b(self):
        """Width (3.0, 3.5] is grade B."""
        assert _classify_width(3.01) == "B"
        assert _classify_width(3.25) == "B"
        assert _classify_width(3.5) == "B"

    def test_width_grade_c(self):
        """Width (3.5, 3.75] is grade C."""
        assert _classify_width(3.51) == "C"
        assert _classify_width(3.6) == "C"
        assert _classify_width(3.75) == "C"

    def test_width_grade_d(self):
        """Width (3.75, 4.5] is grade D."""
        assert _classify_width(3.76) == "D"
        assert _classify_width(4.0) == "D"
        assert _classify_width(4.5) == "D"

    def test_width_grade_e(self):
        """Width >4.5 is grade E."""
        assert _classify_width(4.51) == "E"
        assert _classify_width(5.0) == "E"
        assert _classify_width(10.0) == "E"


# ── Length classification (lowbed) ──

class TestLengthClassificationLowbed:
    def test_length_grade_a_lowbed(self):
        """Length <=17 is grade A for tractor+lowbed."""
        assert _classify_length(10.0, "lowbed") == "A"
        assert _classify_length(17.0, "lowbed") == "A"

    def test_length_grade_b_lowbed(self):
        """Length (17, 22] is grade B for tractor+lowbed."""
        assert _classify_length(17.01, "lowbed") == "B"
        assert _classify_length(20.0, "lowbed") == "B"
        assert _classify_length(22.0, "lowbed") == "B"

    def test_length_grade_c_lowbed(self):
        """Length (22, 30] is grade C for tractor+lowbed."""
        assert _classify_length(22.01, "lowbed") == "C"
        assert _classify_length(26.0, "lowbed") == "C"
        assert _classify_length(30.0, "lowbed") == "C"

    def test_length_grade_d_lowbed(self):
        """Length (30, 35] is grade D for tractor+lowbed."""
        assert _classify_length(30.01, "lowbed") == "D"
        assert _classify_length(32.0, "lowbed") == "D"
        assert _classify_length(35.0, "lowbed") == "D"

    def test_length_grade_e_lowbed(self):
        """Length >35 is grade E for tractor+lowbed."""
        assert _classify_length(35.01, "lowbed") == "E"
        assert _classify_length(40.0, "lowbed") == "E"


# ── Length classification (hydraulic) ──

class TestLengthClassificationHydraulic:
    def test_length_grade_a_hydraulic(self):
        """Length <=22 is grade A for tractor+hydraulic."""
        assert _classify_length(22.0, "hydraulic") == "A"

    def test_length_grade_b_hydraulic(self):
        """Length (22, 31] is grade B for tractor+hydraulic."""
        assert _classify_length(22.01, "hydraulic") == "B"
        assert _classify_length(31.0, "hydraulic") == "B"

    def test_length_grade_c_hydraulic(self):
        """Length (31, 41] is grade C for tractor+hydraulic."""
        assert _classify_length(31.01, "hydraulic") == "C"
        assert _classify_length(41.0, "hydraulic") == "C"

    def test_length_grade_d_hydraulic(self):
        """Length (41, 45] is grade D for tractor+hydraulic."""
        assert _classify_length(41.01, "hydraulic") == "D"
        assert _classify_length(45.0, "hydraulic") == "D"

    def test_length_grade_e_hydraulic(self):
        """Length >45 is grade E for tractor+hydraulic."""
        assert _classify_length(45.01, "hydraulic") == "E"


# ── Height classification ──

class TestHeightClassification:
    def test_height_below_oversized(self):
        """Height <=4.0 is grade A (not oversized by height)."""
        assert _classify_height(3.5) == "A"
        assert _classify_height(4.0) == "A"

    def test_height_grade_a_range(self):
        """Height (4.0, 4.5] is grade A baseline."""
        assert _classify_height(4.01) == "A"
        assert _classify_height(4.3) == "A"
        assert _classify_height(4.5) == "A"

    def test_height_grade_d(self):
        """Height (4.5, 5.0] is grade D."""
        assert _classify_height(4.51) == "D"
        assert _classify_height(4.8) == "D"
        assert _classify_height(5.0) == "D"

    def test_height_grade_e(self):
        """Height >5.0 is grade E."""
        assert _classify_height(5.01) == "E"
        assert _classify_height(6.0) == "E"


# ── classify_size integration ──

class TestClassifySize:
    def test_all_a(self):
        """Vehicle within all A-grade boundaries."""
        result = classify_size(length=17.0, width=3.0, height=4.5)
        assert result["grade"] == "A"
        assert result["width_grade"] == "A"
        assert result["length_grade"] == "A"
        assert result["height_grade"] == "A"

    def test_width_dominates(self):
        """Width grade D should make overall grade D."""
        result = classify_size(length=17.0, width=4.0, height=4.0)
        assert result["grade"] == "D"
        assert result["width_grade"] == "D"
        assert result["length_grade"] == "A"
        assert result["height_grade"] == "A"

    def test_length_dominates(self):
        """Length grade D should make overall grade D."""
        result = classify_size(length=33.0, width=3.0, height=4.0)
        assert result["grade"] == "D"
        assert result["width_grade"] == "A"
        assert result["length_grade"] == "D"
        assert result["height_grade"] == "A"

    def test_height_dominates(self):
        """Height grade D should make overall grade D."""
        result = classify_size(length=17.0, width=3.0, height=4.8)
        assert result["grade"] == "D"
        assert result["width_grade"] == "A"
        assert result["length_grade"] == "A"
        assert result["height_grade"] == "D"

    def test_grade_e_overall(self):
        """Extreme vehicle should be grade E."""
        result = classify_size(length=40.0, width=5.0, height=6.0)
        assert result["grade"] == "E"

    def test_trailer_type_hydraulic(self):
        """Hydraulic trailer has different length thresholds."""
        # 25m with hydraulic trailer = grade B (<=31)
        result = classify_size(length=25.0, width=3.0, height=4.0, trailer_type="hydraulic")
        assert result["grade"] == "B"
        assert result["length_grade"] == "B"
        assert result["trailer_type"] == "hydraulic"

    def test_trailer_type_lowbed(self):
        """Same 25m with lowbed trailer = grade C (>22)"""
        result = classify_size(length=25.0, width=3.0, height=4.0, trailer_type="lowbed")
        assert result["grade"] == "C"
        assert result["length_grade"] == "C"

    def test_details_structure(self):
        """Result should contain detailed breakdown."""
        result = classify_size(length=25.0, width=3.6, height=4.8)
        assert "details" in result
        assert "width" in result["details"]
        assert "length" in result["details"]
        assert "height" in result["details"]
        assert result["details"]["width"]["value"] == 3.6
        assert result["details"]["length"]["value"] == 25.0
        assert result["details"]["height"]["value"] == 4.8


# ── Axle load classification ──

class TestAxleLoadClassification:
    def test_grade_a(self):
        """Axle load <=8t is grade A."""
        result = classify_axle_load(5.0)
        assert result["grade"] == "A"
        result = classify_axle_load(8.0)
        assert result["grade"] == "A"

    def test_grade_b(self):
        """Axle load (8, 10] is grade B."""
        result = classify_axle_load(8.01)
        assert result["grade"] == "B"
        result = classify_axle_load(10.0)
        assert result["grade"] == "B"

    def test_grade_c(self):
        """Axle load (10, 14] is grade C."""
        result = classify_axle_load(10.01)
        assert result["grade"] == "C"
        result = classify_axle_load(14.0)
        assert result["grade"] == "C"

    def test_grade_d(self):
        """Axle load (14, 18] is grade D."""
        result = classify_axle_load(14.01)
        assert result["grade"] == "D"
        result = classify_axle_load(18.0)
        assert result["grade"] == "D"

    def test_grade_e(self):
        """Axle load (18, 20] is grade E."""
        result = classify_axle_load(18.01)
        assert result["grade"] == "E"
        result = classify_axle_load(20.0)
        assert result["grade"] == "E"

    def test_beyond_e(self):
        """Axle load >20 is still E (beyond standard range)."""
        result = classify_axle_load(25.0)
        assert result["grade"] == "E"
        assert "超出分级范围" in result["range"]


# ── Combined classification ──

class TestClassifyCombined:
    def test_basic_combined(self):
        """Standard tractor-trailer should classify correctly."""
        info = {
            "length": 24.0,
            "width": 4.9,
            "height": 4.7,
            "total_weight": 150.0,
            "axis_weight": 18.0,
            "axis_count": 8,
        }
        result = classify_combined(info)
        assert "size_grade" in result
        assert "axle_load_grade" in result
        assert "combined_grade" in result
        assert result["is_oversized"] is True
        # Width 4.9 -> E, Height 4.7 -> D, Length 24 -> C (lowbed)
        # Size grade = max(E, C, D) = E
        assert result["size_grade"] == "E"
        # Axle load 18 -> D
        assert result["axle_load_grade"] == "D"
        # Combined = max(E, D) = E
        assert result["combined_grade"] == "E"

    def test_normal_vehicle(self):
        """A normal vehicle within all limits should be grade A and not oversized."""
        info = {
            "length": 17.0,
            "width": 2.55,
            "height": 4.0,
            "total_weight": 49.0,
            "axis_weight": 8.0,
            "axis_count": 6,
        }
        result = classify_combined(info)
        assert result["size_grade"] == "A"
        assert result["axle_load_grade"] == "A"
        assert result["combined_grade"] == "A"
        assert result["is_oversized"] is False

    def test_axle_load_dominates(self):
        """High axle load should push combined grade up."""
        info = {
            "length": 17.0,
            "width": 2.55,
            "height": 4.0,
            "total_weight": 80.0,
            "axis_weight": 19.0,
            "axis_count": 6,
        }
        result = classify_combined(info)
        assert result["size_grade"] == "A"
        assert result["axle_load_grade"] == "E"
        assert result["combined_grade"] == "E"
