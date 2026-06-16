"""
Unified Risk Assessment Service.

Combines: weather risk + traffic congestion + bridge safety + construction matching
into a single comprehensive risk assessment.
"""
import logging

from app.services.weather_service import weather_service
from app.services.traffic_service import traffic_service

logger = logging.getLogger(__name__)


class RiskService:
    """Comprehensive risk assessment combining all risk dimensions."""

    @staticmethod
    async def assess_comprehensive_risk(
        route_data: dict,
        vehicle_info: dict,
        bridge_assessment: dict = None,
        construction_match: dict = None,
        departure_time: str = None,
    ) -> dict:
        """Assess all risks for a transport route.

        Args:
            route_data: Route from Amap API
            vehicle_info: Vehicle parameters
            bridge_assessment: Optional pre-computed bridge assessment
            construction_match: Optional pre-computed construction match
            departure_time: Optional departure time

        Returns:
            {
                "overall_risk": "低/中/高/极高/禁行",
                "risk_score": 85,  # 0-100, higher = safer
                "dimensions": {
                    "weather": {...},
                    "traffic": {...},
                    "bridge": {...},
                    "construction": {...},
                    "dimension": {...},
                },
                "critical_warnings": [...],
                "all_clear": bool,
                "go_no_go": "GO/CONDITIONAL_GO/NO_GO",
            }
        """
        risks = {}
        critical_warnings = []

        # ── 1. Weather Risk ──
        weather_result = await weather_service.get_route_weather(
            route_data, departure_time
        )
        risks["weather"] = {
            "risk_level": weather_result.get("overall_risk", "低"),
            "warnings": weather_result.get("warnings", []),
        }
        if weather_result.get("overall_risk") == "禁行":
            critical_warnings.append("天气条件不允许: " + "; ".join(weather_result.get("warnings", [])[:3]))
        elif weather_result.get("overall_risk") == "高":
            critical_warnings.append("天气风险较高: " + "; ".join(weather_result.get("warnings", [])[:2]))

        # ── 2. Traffic Risk ──
        traffic_result = traffic_service.analyze_traffic(route_data)
        risks["traffic"] = {
            "condition": traffic_result.get("overall_condition", "未知"),
            "delay_minutes": traffic_result.get("total_delay_minutes", 0),
        }
        if traffic_result.get("total_delay_minutes", 0) > 30:
            critical_warnings.append(f"预计交通延误{traffic_result['total_delay_minutes']}分钟")

        # ── 3. Bridge Risk (from existing assessment) ──
        if bridge_assessment:
            risks["bridge"] = {
                "risk_level": bridge_assessment.get("risk_level", "未知"),
                "risky_bridges": bridge_assessment.get("risky_bridges", 0),
                "max_ratio": bridge_assessment.get("max_effect_ratio", 0),
            }
            if bridge_assessment.get("risky_bridges", 0) > 0:
                critical_warnings.append(f"{bridge_assessment['risky_bridges']}座桥梁存在通行风险")
        else:
            risks["bridge"] = {"risk_level": "未评估", "risky_bridges": 0}

        # ── 4. Construction Risk ──
        if construction_match:
            risks["construction"] = {
                "matching_events": construction_match.get("matching_events", 0),
            }
            if construction_match.get("matching_events", 0) > 3:
                critical_warnings.append(f"路线经过{construction_match['matching_events']}处施工路段")
        else:
            risks["construction"] = {"matching_events": 0}

        # ── 5. Dimension Risk ──
        from app.services.regulation_kb import regulation_kb
        compliance = regulation_kb.check_dimension_compliance(vehicle_info)
        violations = compliance.get("violations", [])
        risks["dimension"] = {
            "violations": len(violations),
            "details": violations[:5],
        }

        # ── Compute overall risk ──
        risk_scores = {
            "低": 0, "中": 1, "高": 2, "极高": 3, "禁行": 5,
        }
        max_score = 0

        # Weather
        w_risk = weather_result.get("overall_risk", "低")
        max_score = max(max_score, risk_scores.get(w_risk, 0))

        # Bridge
        if bridge_assessment:
            b_risk = bridge_assessment.get("risk_level", "低")
            max_score = max(max_score, risk_scores.get(b_risk, 0))

        # Construction
        const_count = construction_match.get("matching_events", 0) if construction_match else 0
        if const_count > 5:
            max_score = max(max_score, 2)
        elif const_count > 2:
            max_score = max(max_score, 1)

        # Traffic
        if traffic_result.get("total_delay_minutes", 0) > 60:
            max_score = max(max_score, 1)

        # Map score back to level
        score_to_level = {0: "低", 1: "中", 2: "高", 3: "极高", 5: "禁行"}
        overall_risk = score_to_level.get(max_score, "低")

        # Safety score (0-100, higher = safer)
        safety_score = max(0, 100 - max_score * 25)

        # GO/NO_GO decision
        if max_score >= 5:
            go_decision = "NO_GO"
        elif max_score >= 2:
            go_decision = "CONDITIONAL_GO"
        else:
            go_decision = "GO"

        return {
            "overall_risk": overall_risk,
            "risk_score": safety_score,
            "dimensions": risks,
            "critical_warnings": critical_warnings[:5],
            "all_clear": len(critical_warnings) == 0,
            "go_no_go": go_decision,
        }

    @staticmethod
    def format_for_llm(risk_result: dict) -> str:
        """Format comprehensive risk for LLM."""
        if not risk_result:
            return ""
        lines = [
            "【综合风险评估】",
            f"整体风险: {risk_result.get('overall_risk', '未知')} (安全分: {risk_result.get('risk_score', 0)}/100)",
            f"通行建议: {'可通行' if risk_result.get('go_no_go') == 'GO' else '条件通行' if risk_result.get('go_no_go') == 'CONDITIONAL_GO' else '不建议通行'}",
        ]
        if risk_result.get("critical_warnings"):
            lines.append("关键风险:")
            for w in risk_result["critical_warnings"]:
                lines.append(f"  [!] {w}")
        return "\n".join(lines)


risk_service = RiskService()
