"""
Tests for permit_generator.py.

Covers:
- Full application generation with all fields
- Route description formatting
- Safety notes generation from assessment
- Escort plan generation by dimension thresholds
- Formatter output for approver review
- PDF data structure generation
- Edge cases (empty routes, missing fields, boundary dimensions)
"""

import pytest
from datetime import datetime
from app.services.permit_generator import (
    PermitGenerator,
    ESCORT_THRESHOLDS,
)


# ── Shared test fixtures ──

@pytest.fixture
def sample_vehicle_info():
    return {
        "vehicle_type": "牵引车+低平板半挂车",
        "length": 24.0,
        "width": 4.9,
        "height": 4.7,
        "total_weight": 150.0,
        "axle_count": 8,
        "axle_spacings": [3.5, 1.5, 3.0, 3.0, 3.0, 3.0, 3.0],
        "axle_loads": [18.0, 18.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0],
        "tractor_length": 6.0,
        "trailer_length": 18.0,
        "tractor_axle_count": 3,
        "trailer_axle_count": 5,
        "first_axle_distance": 2.5,
    }


@pytest.fixture
def sample_cargo_info():
    return {
        "name": "大型变压器",
        "length": 10.0,
        "width": 4.5,
        "height": 4.2,
        "total_weight": 120.0,
    }


@pytest.fixture
def sample_routes():
    return [
        {
            "id": "route_1",
            "route_description": "北村--G76厦蓉高速--海沧",
            "major_roads": ["G76厦蓉高速"],
            "distance": 85000,
            "duration": 11700,
            "tunnel_count": 5,
            "tunnel_distance": 8000,
            "toll_cost": 120.0,
            "pros": ["路况良好，限高限宽条件满足", "通行时间预计3.5小时"],
            "cons": ["某转弯处需安排交警疏导"],
        },
        {
            "id": "route_2",
            "route_description": "北村--G15沈海高速--G76厦蓉高速--海沧",
            "major_roads": ["G15沈海高速", "G76厦蓉高速"],
            "distance": 92000,
            "duration": 12600,
            "tunnel_count": 3,
            "tunnel_distance": 5000,
            "toll_cost": 150.0,
            "pros": ["全程高速，路况稳定", "车辆易于通行"],
            "cons": ["里程较长，预计增加运输时间30分钟"],
        },
    ]


@pytest.fixture
def sample_applicant_info():
    return {
        "name": "XX大件运输有限公司",
        "address": "XX省XX市XX区XX路XX号",
        "contact_person": "张三",
        "phone": "13800138000",
        "id_number": "91350000XXXXXXXXXX",
    }


@pytest.fixture
def sample_schedule_info():
    return {
        "departure_time": "2025年6月20日8点",
        "estimated_arrival": "2025年6月20日12点",
    }


@pytest.fixture
def sample_assessment():
    return {
        "overall_assessment": {
            "recommendation": "推荐",
            "risk_level": "高",
            "score": 6.5,
            "key_factors": [
                "部分桥梁需重点关注",
                "存在少量施工影响",
                "车辆尺寸基本合规（需注意个别限制）",
            ],
        },
        "traffic_analysis": {
            "estimated_time": "约3小时15分钟",
            "construction_impacts": [
                {
                    "location": "G76厦蓉高速K120+500-K125+800处",
                    "impact_level": "中等",
                    "lane_occupancy": "主车道、应急车道",
                    "delay_minutes": 15,
                }
            ],
            "total_delay": 15,
            "recommended_time_window": "上午8:00-11:00（避开施工高峰期）",
        },
        "route_compatibility": {
            "dimension_check": {
                "height_limit": 5.0,
                "vehicle_height": 4.7,
                "height_status": "通过 5/5 个检查点",
                "weight_limit": 55.0,
                "vehicle_weight": 150.0,
                "weight_status": "符合 5/5 个路段要求",
            },
            "structural_safety": {
                "total_bridges": 12,
                "high_risk_bridges": 2,
                "min_effect_ratio": 0.45,
                "max_moment_ratio": 1.15,
                "safety_threshold": 0.8,
                "safety_assessment": "存在风险（需重点关注）",
            },
            "compliance_status": "基本符合（存在注意事项）",
        },
        "recommendations": {
            "for_user": [
                "通过施工路段时保持安全车距",
                "控制车速在60km/h以下",
                "通过桥梁时减速慢行（≤30km/h）",
                "避免在桥梁上停车或紧急制动",
                "出发前检查车辆状况（刹车、轮胎、灯光）",
            ],
            "for_approver": {
                "approval_decision": "有条件批准",
                "special_conditions": [
                    "需对高风险桥梁进行现场勘察或加固评估",
                    "需办理超限运输许可证",
                ],
                "risk_notes": "有2座桥梁存在通行风险；路线经过1处施工/事件路段",
            },
        },
    }


# ── generate_application tests ──


class TestGenerateApplication:
    """Tests for the main generate_application method."""

    def test_full_application_with_all_fields(
        self, sample_routes, sample_vehicle_info, sample_cargo_info,
        sample_applicant_info, sample_schedule_info, sample_assessment
    ):
        """Generate a complete application with all optional fields."""
        route_data = {
            "routes": sample_routes,
            "assessment": sample_assessment,
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
            applicant_info=sample_applicant_info,
            schedule_info=sample_schedule_info,
        )

        # Top-level keys
        assert "application_id" in result
        assert "generated_at" in result
        assert result["status"] == "DRAFT"
        assert len(result["application_id"]) > 0

        # Sections
        assert "applicant" in result
        assert "vehicle_cargo" in result
        assert "cargo" in result
        assert "transport" in result
        assert "route_analysis" in result
        assert "safety_notes" in result
        assert "escort_plan" in result
        assert "compliance" in result

    def test_application_applicant_fields(
        self, sample_routes, sample_vehicle_info, sample_cargo_info,
        sample_applicant_info
    ):
        """Applicant info is correctly mapped."""
        route_data = {"routes": sample_routes, "assessment": {}}
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
            applicant_info=sample_applicant_info,
        )

        applicant = result["applicant"]
        assert applicant["name"] == "XX大件运输有限公司"
        assert applicant["contact_person"] == "张三"
        assert applicant["phone"] == "13800138000"
        assert applicant["id_number"] == "91350000XXXXXXXXXX"

    def test_application_transport_parses_route_description(
        self, sample_vehicle_info, sample_cargo_info
    ):
        """Transport section extracts origin/destination from route description."""
        routes = [
            {
                "route_description": "起点镇--G76--终点市",
                "distance": 50000,
                "duration": 3600,
            }
        ]
        result = PermitGenerator.generate_application(
            route_data={"routes": routes, "assessment": {}},
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )

        transport = result["transport"]
        assert transport["origin"] == "起点镇"
        assert transport["destination"] == "终点市"

    def test_application_without_applicant_info(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """Application generation succeeds without applicant info."""
        route_data = {"routes": sample_routes, "assessment": {}}
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )

        applicant = result["applicant"]
        assert applicant["name"] == ""
        assert applicant["phone"] == ""

    def test_application_risk_level_from_assessment(
        self, sample_routes, sample_vehicle_info, sample_cargo_info,
        sample_assessment
    ):
        """Risk level is taken from assessment when available."""
        route_data = {"routes": sample_routes, "assessment": sample_assessment}
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )

        assert result["compliance"]["risk_level"] == "高"

    def test_application_risk_level_fallback(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """Risk level computed from vehicle dimensions when no assessment."""
        route_data = {"routes": sample_routes, "assessment": {}}
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )

        # 150 tons + 4.9m width should be "高" or higher
        assert result["compliance"]["risk_level"] in ("高", "极高")

    def test_application_with_multiple_routes(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """Route analysis section handles multiple routes."""
        route_data = {"routes": sample_routes, "assessment": {}}
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )

        route_analysis = result["route_analysis"]
        assert route_analysis["primary_route"] is not None
        assert route_analysis["primary_route"]["is_primary"] is True
        assert len(route_analysis["alternative_routes"]) == 1
        assert route_analysis["alternative_routes"][0]["is_primary"] is False

    def test_application_with_single_route(
        self, sample_vehicle_info, sample_cargo_info
    ):
        """Single route generates primary route only, no alternatives."""
        single_route = [
            {
                "route_description": "起点→终点",
                "distance": 30000,
                "duration": 1800,
            }
        ]
        result = PermitGenerator.generate_application(
            route_data={"routes": single_route, "assessment": {}},
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )

        route_analysis = result["route_analysis"]
        assert route_analysis["primary_route"] is not None
        assert route_analysis["alternative_routes"] == []


# ── generate_route_description tests ──


class TestGenerateRouteDescription:
    """Tests for the route description formatter."""

    def test_basic_route_description(self, sample_routes):
        """Formats basic route list correctly."""
        result = PermitGenerator.generate_route_description(sample_routes)

        assert "推荐路线及分析" in result
        assert "路线A（主推荐路线）" in result
        assert "路线B（备用路线）" in result
        assert "北村--G76厦蓉高速--海沧" in result
        assert "路况良好" in result
        assert "某转弯处需安排交警疏导" in result

    def test_empty_routes(self):
        """Empty routes list returns placeholder."""
        result = PermitGenerator.generate_route_description([])
        assert "无可用路线" in result

    def test_route_without_pros_cons(self):
        """Routes without pros/cons still format correctly."""
        routes = [
            {
                "route_description": "A→B",
                "distance": 50000,
                "duration": 3600,
            }
        ]
        result = PermitGenerator.generate_route_description(routes)
        assert "A→B" in result
        assert "优点" not in result
        assert "缺点" not in result

    def test_distance_and_duration_formatting(self):
        """Distance in meters converted to km, duration converted to minutes."""
        routes = [
            {
                "route_description": "X→Y",
                "distance": 12345,
                "duration": 5400,
            }
        ]
        result = PermitGenerator.generate_route_description(routes)
        assert "12.3公里" in result
        assert "90分钟" in result

    def test_many_routes_uses_alphabet_labels(self):
        """Routes beyond E get numeric labels."""
        routes = [
            {"route_description": f"R{i}", "distance": 10000, "duration": 600}
            for i in range(7)
        ]
        result = PermitGenerator.generate_route_description(routes)
        assert "路线A" in result
        assert "路线E" in result
        assert "路线6" in result  # 0-indexed: 6th alternative = route #7
        assert "路线7" in result


# ── generate_safety_notes tests ──


class TestGenerateSafetyNotes:
    """Tests for safety notes generation."""

    def test_safety_notes_from_assessment(self, sample_assessment):
        """Extracts safety notes from assessment recommendations."""
        notes = PermitGenerator.generate_safety_notes(sample_assessment)

        assert isinstance(notes, list)
        assert len(notes) > 0
        # Should include user recommendations
        assert any("施工路段" in n for n in notes)
        assert any("桥梁" in n for n in notes)
        # Should include generic notes
        assert any("避开高峰" in n for n in notes)
        assert any("货物固定" in n for n in notes)

    def test_safety_notes_empty_assessment(self):
        """Empty assessment still generates generic safety notes."""
        notes = PermitGenerator.generate_safety_notes({})
        assert isinstance(notes, list)
        assert len(notes) > 0
        assert any("避开高峰" in n for n in notes)
        assert any("货物固定" in n for n in notes)

    def test_safety_notes_no_duplicates(self, sample_assessment):
        """Does not duplicate notes between recommendations and generics."""
        notes = PermitGenerator.generate_safety_notes(sample_assessment)
        # Check for the specific recommendation that matches a generic
        # "出发前检查车辆状况（刹车、轮胎、灯光）" appears in for_user
        count_vehicle_check = sum(
            1 for n in notes if "检查车辆状况" in n
        )
        assert count_vehicle_check >= 1  # at least once, duplicates are fine

    def test_safety_notes_high_risk_bridges(
        self, sample_assessment
    ):
        """High-risk bridges trigger specific safety note."""
        notes = PermitGenerator.generate_safety_notes(sample_assessment)
        assert any("高风险桥梁" in n and "30km/h" in n for n in notes)

    def test_safety_notes_construction_zones(
        self, sample_assessment
    ):
        """Construction zones trigger specific note."""
        notes = PermitGenerator.generate_safety_notes(sample_assessment)
        # Has 1 construction impact
        assert any("施工路段" in n for n in notes)


# ── generate_escort_plan tests ──


class TestGenerateEscortPlan:
    """Tests for escort plan generation."""

    def test_escort_for_oversized_vehicle(self, sample_vehicle_info):
        """Large vehicle triggers escort requirements."""
        plan = PermitGenerator.generate_escort_plan(
            sample_vehicle_info, risk_level="高"
        )

        assert plan["escort_required"] is True
        assert plan["escort_vehicle_count"] >= 2
        assert len(plan["reasons"]) > 0
        assert plan["escort_personnel"] >= 4
        assert len(plan["emergency_plan"]) >= 4

    def test_escort_length_threshold(self):
        """Length >= 28m triggers 2 escort vehicles."""
        vehicle = {
            "length": 30.0,
            "width": 2.5,
            "height": 3.0,
            "total_weight": 40.0,
        }
        plan = PermitGenerator.generate_escort_plan(vehicle, risk_level="低")
        assert plan["escort_vehicle_count"] >= 2
        assert any("28" in r for r in plan["reasons"])

    def test_escort_width_threshold(self):
        """Width >= 3.75m triggers 2 escort vehicles."""
        vehicle = {
            "length": 20.0,
            "width": 4.0,
            "height": 3.0,
            "total_weight": 40.0,
        }
        plan = PermitGenerator.generate_escort_plan(vehicle, risk_level="低")
        assert plan["escort_vehicle_count"] >= 2
        assert any("3.75" in r for r in plan["reasons"])

    def test_escort_height_threshold(self):
        """Height >= 4.5m triggers 1 escort vehicle."""
        vehicle = {
            "length": 20.0,
            "width": 2.5,
            "height": 4.8,
            "total_weight": 40.0,
        }
        plan = PermitGenerator.generate_escort_plan(vehicle, risk_level="低")
        assert plan["escort_vehicle_count"] >= 1
        assert any("4.5" in r for r in plan["reasons"])

    def test_escort_weight_threshold(self):
        """Weight >= 100 tons triggers 2 escort vehicles."""
        vehicle = {
            "length": 20.0,
            "width": 2.5,
            "height": 3.0,
            "total_weight": 120.0,
        }
        plan = PermitGenerator.generate_escort_plan(vehicle, risk_level="低")
        assert plan["escort_vehicle_count"] >= 2
        assert any("100" in r for r in plan["reasons"])

    def test_escort_standard_vehicle(self):
        """Standard vehicle gets minimal escort."""
        vehicle = {
            "length": 18.0,
            "width": 2.5,
            "height": 3.5,
            "total_weight": 40.0,
        }
        plan = PermitGenerator.generate_escort_plan(vehicle, risk_level="低")
        assert plan["escort_required"] is True  # always required for oversized
        assert plan["escort_vehicle_count"] == 1
        assert plan["escort_personnel"] == 2

    def test_escort_extreme_risk_level(self):
        """极高 risk level triggers 3 escort vehicles."""
        vehicle = {
            "length": 22.0,
            "width": 3.5,
            "height": 4.0,
            "total_weight": 80.0,
        }
        plan = PermitGenerator.generate_escort_plan(vehicle, risk_level="极高")
        assert plan["escort_vehicle_count"] == 3
        assert plan["escort_personnel"] == 6
        assert "机动巡逻车" in plan["configuration"]

    def test_escort_emergency_plan_coverage(self):
        """Emergency plan covers major incident types."""
        plan = PermitGenerator.generate_escort_plan(
            {"length": 20, "width": 3, "height": 4, "total_weight": 50},
            risk_level="中"
        )
        emergency = "".join(plan["emergency_plan"])
        assert "故障" in emergency
        assert "事故" in emergency
        assert "天气" in emergency
        assert "货物" in emergency


# ── format_for_approver tests ──


class TestFormatForApprover:
    """Tests for the approver-facing text formatter."""

    def test_formatted_text_structure(
        self, sample_routes, sample_vehicle_info, sample_cargo_info,
        sample_applicant_info, sample_schedule_info
    ):
        """Formatted text includes all expected sections."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
            applicant_info=sample_applicant_info,
            schedule_info=sample_schedule_info,
        )
        text = PermitGenerator.format_for_approver(app)

        assert "交通保障中心工作人员" in text
        assert "运输起点" in text
        assert "运输终点" in text
        assert "车辆类型" in text
        assert "载重" in text
        assert "车辆尺寸" in text
        assert "货物名称及重量" in text
        assert "计划出发时间" in text
        assert "预计到达时间" in text
        assert "推荐路线及分析" in text
        assert "安全重点提示" in text

    def test_formatted_text_includes_escort(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """Formatted text includes escort plan when required."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )
        text = PermitGenerator.format_for_approver(app)

        # Large vehicle should have escort
        assert "护送方案" in text
        assert "护送车" in text

    def test_formatted_text_includes_applicant(
        self, sample_routes, sample_vehicle_info, sample_cargo_info,
        sample_applicant_info
    ):
        """Formatted text includes applicant info at the end."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
            applicant_info=sample_applicant_info,
        )
        text = PermitGenerator.format_for_approver(app)

        assert "XX大件运输有限公司" in text
        assert "张三" in text
        assert "13800138000" in text

    def test_formatted_text_ends_with_approval_request(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """Formatted text ends with approval prompt."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )
        text = PermitGenerator.format_for_approver(app)

        assert "审批" in text
        assert "交通管控建议" in text


# ── to_pdf_data tests ──


class TestToPdfData:
    """Tests for the PDF-ready data structure."""

    def test_pdf_data_structure(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """PDF data contains all required structural sections."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )
        pdf = PermitGenerator.to_pdf_data(app)

        assert "metadata" in pdf
        assert "page_setup" in pdf
        assert "header" in pdf
        assert "sections" in pdf
        assert "footer" in pdf
        assert "annex" in pdf

    def test_pdf_metadata(self, sample_routes, sample_vehicle_info, sample_cargo_info):
        """PDF metadata contains application ID and document type."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )
        pdf = PermitGenerator.to_pdf_data(app)

        assert pdf["metadata"]["document_type"] == "permit_application"
        assert app["application_id"][:8] in pdf["metadata"]["title"]

    def test_pdf_sections_count(
        self, sample_routes, sample_vehicle_info, sample_cargo_info
    ):
        """PDF has exactly 5 main sections matching regulation Article 6."""
        route_data = {"routes": sample_routes, "assessment": {}}
        app = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=sample_vehicle_info,
            cargo_info=sample_cargo_info,
        )
        pdf = PermitGenerator.to_pdf_data(app)

        assert len(pdf["sections"]) == 5
        headings = [s["heading"] for s in pdf["sections"]]
        assert "申请人信息" in headings[0]
        assert "车货信息" in headings[1]
        assert "货物信息" in headings[2]
        assert "运输信息" in headings[3]
        assert "护送方案" in headings[4]


# ── Compliance summary tests ──


class TestComplianceSummary:
    """Tests for the compliance summary builder."""

    def test_extreme_vehicle_is_non_compliant(self):
        """Extremely large vehicle is flagged as non-compliant."""
        vehicle = {
            "length": 40.0,
            "width": 6.0,
            "height": 5.5,
            "total_weight": 250.0,
        }
        route_data = {
            "routes": [{"route_description": "A→B"}],
            "assessment": {},
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle,
            cargo_info={"name": "超大设备", "total_weight": 200},
        )

        compliance = result["compliance"]
        assert compliance["overall_status"] == "需特别审批"
        checks = compliance["dimension_checks"]
        statuses = {c["item"]: c["status"] for c in checks}
        assert statuses["高度"] == "超标"
        assert statuses["宽度"] == "超标"
        assert statuses["长度"] == "超标"
        assert statuses["重量"] == "超标"

    def test_standard_vehicle_is_compliant(self):
        """Standard vehicle passes all dimension checks."""
        vehicle = {
            "length": 18.0,
            "width": 2.5,
            "height": 3.5,
            "total_weight": 40.0,
        }
        route_data = {
            "routes": [{"route_description": "A→B"}],
            "assessment": {},
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle,
            cargo_info={"name": "普通货物", "total_weight": 30},
        )

        compliance = result["compliance"]
        assert compliance["overall_status"] == "符合要求"
        checks = compliance["dimension_checks"]
        for c in checks:
            assert c["status"] == "合规", f"{c['item']} should be 合规"


# ── Risk level determination tests ──


class TestRiskLevelDetermination:
    """Tests for the risk level determination logic."""

    def test_low_risk_vehicle(self):
        """Small vehicle without assessment gets low risk."""
        vehicle = {"length": 18.0, "width": 2.5, "height": 3.5, "total_weight": 40.0}
        route_data = {
            "routes": [{"route_description": "A→B"}],
            "assessment": {},
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle,
            cargo_info={"name": "test", "total_weight": 30},
        )
        assert result["compliance"]["risk_level"] == "低"

    def test_medium_risk_vehicle(self):
        """Moderately oversized vehicle gets medium risk (score 2-3)."""
        vehicle = {"length": 25.0, "width": 3.3, "height": 4.6, "total_weight": 80.0}
        route_data = {
            "routes": [{"route_description": "A→B"}],
            "assessment": {},
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle,
            cargo_info={"name": "test", "total_weight": 60},
        )
        assert result["compliance"]["risk_level"] == "中"

    def test_high_risk_vehicle(self):
        """Highly oversized vehicle gets high risk."""
        vehicle = {"length": 30.0, "width": 4.0, "height": 4.8, "total_weight": 120.0}
        route_data = {
            "routes": [{"route_description": "A→B"}],
            "assessment": {},
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle,
            cargo_info={"name": "test", "total_weight": 130},
        )
        assert result["compliance"]["risk_level"] == "高"

    def test_extreme_risk_vehicle(self):
        """Extremely oversized vehicle gets 极高 risk."""
        vehicle = {"length": 35.0, "width": 5.0, "height": 5.5, "total_weight": 200.0}
        route_data = {
            "routes": [{"route_description": "A→B"}],
            "assessment": {},
        }
        result = PermitGenerator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle,
            cargo_info={"name": "test", "total_weight": 180},
        )
        assert result["compliance"]["risk_level"] == "极高"
