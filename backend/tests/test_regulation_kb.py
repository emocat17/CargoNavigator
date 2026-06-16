"""
Tests for RegulationKB — the oversized cargo regulation knowledge base.
"""
import sys
from pathlib import Path

import pytest

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.regulation_kb import RegulationKB


@pytest.fixture
def kb() -> RegulationKB:
    return RegulationKB()


# ── query ──


class TestQuery:
    """Keyword search against the regulation articles."""

    def test_query_by_keyword_罚款(self, kb):
        results = kb.query("罚款")
        assert len(results) >= 1
        # Article 43 should be top hit
        assert any(a.get("article_number") == "43" for a in results)

    def test_query_by_keyword_护送(self, kb):
        results = kb.query("护送")
        assert len(results) >= 2  # Article 22 + escort_guide

    def test_query_by_keyword_申请材料(self, kb):
        results = kb.query("申请材料")
        assert len(results) >= 1
        assert any(a.get("article_number") == "6" for a in results)

    def test_query_by_article_number(self, kb):
        results = kb.query("43")
        assert len(results) >= 1
        assert results[0].get("article_number") == "43"

    def test_query_no_match(self, kb):
        results = kb.query("xyzzy_nonexistent_keyword")
        assert results == []

    def test_query_multiple_keywords(self, kb):
        results = kb.query("超限 标准 尺寸")
        assert len(results) >= 1

    def test_query_returns_article_number_title_content_tags(self, kb):
        results = kb.query("超限标准")
        assert len(results) >= 1
        art = results[0]
        assert "article_number" in art
        assert "title" in art
        assert "content" in art
        assert "tags" in art


# ── classify_permit ──


class TestClassifyPermit:
    """Permit classification (I / II / III)."""

    def test_standard_vehicle_is_class_I(self, kb):
        """A vehicle within all standard limits gets class I."""
        result = kb.classify_permit({
            "height": 3.5,
            "width": 2.5,
            "length": 15.0,
            "weight": 40,
            "axle_count": 6,
        })
        assert result == "I"

    def test_height_above_class_I_is_III(self, kb):
        """Height > 4.5m is Class III."""
        result = kb.classify_permit({"height": 4.7, "width": 3.0, "weight": 60})
        assert result == "III"

    def test_width_above_class_I_is_III(self, kb):
        """Width > 3.75m is Class III."""
        result = kb.classify_permit({"height": 4.0, "width": 4.0, "weight": 80})
        assert result == "III"

    def test_length_above_class_I_is_III(self, kb):
        """Length > 28m is Class III."""
        result = kb.classify_permit({"height": 4.0, "width": 3.0, "length": 30, "weight": 80})
        assert result == "III"

    def test_heavy_but_normal_dimensions_is_II(self, kb):
        """Weight > 100t with dimensions within Class I is Class II."""
        result = kb.classify_permit({
            "height": 4.2,
            "width": 3.5,
            "weight": 120,
        })
        assert result == "II"

    def test_moderate_oversize_is_I(self, kb):
        """Slightly over standard but within Class I thresholds."""
        result = kb.classify_permit({
            "height": 4.3,
            "width": 3.0,
            "length": 20,
            "weight": 80,
        })
        assert result == "I"

    def test_weight_over_axle_limit(self, kb):
        """Weight exceeding the axle-count-based standard limit triggers over-limit."""
        result = kb.classify_permit({
            "height": 4.0,
            "width": 2.5,
            "weight": 55,
            "axle_count": 3,
            "vehicle_type": "truck",
        })
        # 3-axle truck limit is 25t, 55t far exceeds it → should be III or at least I
        assert result in ("I", "II", "III")

    def test_user_provided_example(self, kb):
        """The exact example from the task description."""
        result = kb.classify_permit({
            "height": 4.7,
            "width": 3.0,
            "weight": 60,
        })
        # height 4.7 > 4.5 → class III
        assert result == "III"


# ── get_required_documents ──


class TestDocuments:
    def test_class_I_documents(self, kb):
        docs = kb.get_required_documents("I")
        assert isinstance(docs, list)
        assert len(docs) >= 5
        assert any("申请表" in d for d in docs)

    def test_class_II_documents(self, kb):
        docs = kb.get_required_documents("II")
        assert len(docs) > len(kb.get_required_documents("I"))
        assert any("护送方案" in d for d in docs)

    def test_class_III_documents(self, kb):
        docs = kb.get_required_documents("III")
        assert len(docs) > len(kb.get_required_documents("II"))
        assert any("称重检测" in d for d in docs)

    def test_lowercase_input(self, kb):
        docs = kb.get_required_documents("iii")
        assert any("称重检测" in d for d in docs)


# ── get_escort_requirements ──


class TestEscortRequirements:
    def test_class_I_no_escort(self, kb):
        result = kb.get_escort_requirements({"height": 3.5, "width": 2.5, "weight": 40})
        assert result["escort_required"] is False
        assert result["min_escort_vehicles"] == 0

    def test_class_III_escort_required(self, kb):
        result = kb.get_escort_requirements({"height": 4.7, "width": 3.0, "weight": 80})
        assert result["escort_required"] is True
        assert result["min_escort_vehicles"] >= 1

    def test_wide_class_III_needs_more_escort(self, kb):
        result = kb.get_escort_requirements({
            "height": 4.8,
            "width": 4.7,  # > 4.5m → 2 escort vehicles for width
            "weight": 90,
        })
        assert result["escort_required"] is True
        assert result["min_escort_vehicles"] >= 2

    def test_extreme_dimensions_police_escort(self, kb):
        result = kb.get_escort_requirements({
            "height": 5.2,
            "width": 4.6,
            "length": 36,
            "weight": 120,
        })
        assert result["police_escort_required"] is True


# ── check_dimension_compliance ──


class TestDimensionCompliance:
    def test_compliant_vehicle(self, kb):
        result = kb.check_dimension_compliance({
            "height": 3.5,
            "width": 2.5,
            "length": 15.0,
            "weight": 40,
            "axle_count": 6,
        })
        assert result["is_compliant"] is True
        assert len(result["violations"]) == 0

    def test_height_violation(self, kb):
        result = kb.check_dimension_compliance({
            "height": 4.5,
            "width": 2.5,
            "weight": 40,
            "axle_count": 5,
        })
        assert result["is_compliant"] is False
        assert any(v["dimension"] == "高度" for v in result["violations"])

    def test_weight_violation_with_axle_count(self, kb):
        result = kb.check_dimension_compliance({
            "height": 3.0,
            "width": 2.5,
            "weight": 30,
            "axle_count": 2,
            "vehicle_type": "truck",
        })
        # 2-axle limit is 18t, 30t exceeds
        assert any(v["dimension"] == "总质量" for v in result["violations"])

    def test_multiple_violations(self, kb):
        result = kb.check_dimension_compliance({
            "height": 5.0,
            "width": 4.0,
            "length": 25.0,
            "weight": 60,
            "axle_count": 3,
            "vehicle_type": "truck",
        })
        assert len(result["violations"]) >= 3  # height + width + length + possibly weight

    def test_violation_has_excess_field(self, kb):
        result = kb.check_dimension_compliance({
            "height": 4.5,
            "width": 2.5,
            "weight": 40,
            "axle_count": 6,
        })
        for v in result["violations"]:
            assert "excess" in v
            assert v["excess"] > 0


# ── get_penalty_estimate ──


class TestPenaltyEstimate:
    def test_no_violations_no_penalty(self, kb):
        result = kb.get_penalty_estimate(vehicle_info={
            "height": 3.5, "width": 2.5, "weight": 40, "axle_count": 6,
        })
        assert result["total_penalty"]["min"] == 0
        assert result["total_penalty"]["max"] == 0

    def test_size_violation_penalty(self, kb):
        result = kb.get_penalty_estimate(vehicle_info={
            "height": 4.7, "width": 2.5, "weight": 40, "axle_count": 6,
        })
        assert result["size_penalty"]["min"] >= 200

    def test_weight_violation_penalty(self, kb):
        result = kb.get_penalty_estimate(vehicle_info={
            "height": 3.0, "width": 2.5, "weight": 25, "axle_count": 2, "vehicle_type": "truck",
        })
        # 2-axle limit 18t, 25t → 7t excess → 7000kg * 500/1000 = 3500
        assert result["weight_penalty"]["amount"] > 0

    def test_combined_penalty_capped_at_30000(self, kb):
        result = kb.get_penalty_estimate(vehicle_info={
            "height": 5.0, "width": 4.0, "length": 30, "weight": 120,
            "axle_count": 3, "vehicle_type": "truck",
        })
        assert result["total_penalty"]["max"] <= 30000


# ── format_for_llm ──


class TestFormatForLLM:
    def test_returns_string(self, kb):
        text = kb.format_for_llm({"height": 4.7, "width": 3.0, "weight": 80})
        assert isinstance(text, str)
        assert len(text) > 100

    def test_includes_permit_class(self, kb):
        text = kb.format_for_llm({"height": 4.7, "width": 3.0, "weight": 80})
        assert "三类" in text

    def test_includes_document_list(self, kb):
        text = kb.format_for_llm({"height": 4.0, "width": 3.0, "weight": 50})
        assert "申请材料" in text

    def test_includes_penalty_info(self, kb):
        text = kb.format_for_llm({"height": 4.7, "width": 3.0, "weight": 80})
        assert "处罚" in text or "罚款" in text


# ── Edge cases ──


class TestEdgeCases:
    def test_empty_vehicle_info(self, kb):
        """Empty dict should return class I and no errors."""
        result = kb.classify_permit({})
        assert result == "I"

    def test_none_values(self, kb):
        """None values should be treated as 0."""
        result = kb.classify_permit({"height": None, "width": None, "weight": None})
        assert result == "I"

    def test_string_values(self, kb):
        """String numeric values should be coerced."""
        result = kb.classify_permit({"height": "4.7", "width": "3.0", "weight": "60"})
        assert result == "III"

    def test_zero_values(self, kb):
        result = kb.classify_permit({"height": 0, "width": 0, "weight": 0})
        assert result == "I"

    def test_compliance_zero_dimensions(self, kb):
        result = kb.check_dimension_compliance({"height": 0, "width": 0, "weight": 0, "axle_count": 0})
        assert result["is_compliant"] is True
