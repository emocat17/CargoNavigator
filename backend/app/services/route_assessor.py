"""
Route Assessment Service.

Comprehensive route safety and feasibility assessment combining:
- Bridge structural safety (via bridge_service)
- Construction/traffic event matching (via construction_matcher)
- Vehicle dimension compliance checks
- Composite scoring (0-10) with recommendations

Produces structured JSON output suitable for both API responses
and downstream LLM prompt generation.
"""
import logging
import re
from datetime import datetime
from typing import Optional

from app.services.bridge_service import bridge_service, _check_space_passability
from app.services.construction_matcher import (
    load_all_events,
    match_events_to_route,
    HIGHWAY_NAME_MAP,
)
from app.services.cost_estimator import cost_estimator
from app.bridge_db import query

logger = logging.getLogger(__name__)

# ── Scoring thresholds ──
SCORE_BRIDGE_ALL_PASS = 4
SCORE_BRIDGE_ONE_RISKY = 2
SCORE_BRIDGE_MANY_RISKY = 0

SCORE_CONSTRUCTION_NONE = 3
SCORE_CONSTRUCTION_SOME = 1
SCORE_CONSTRUCTION_MANY = 0

SCORE_DIMENSION_ALL_PASS = 3
SCORE_DIMENSION_BORDERLINE = 1
SCORE_DIMENSION_FAIL = 0


class RouteAssessor:
    """Composite route assessor for oversized cargo transport."""

    @staticmethod
    def assess_route(
        route_data: dict,
        vehicle_info: dict,
    ) -> dict:
        """Perform a full route assessment and return structured JSON.

        Args:
            route_data: Route information. Expected keys:
                - route_description: str  (e.g. "北村--G76--天宝--G76--海沧")
                - major_roads: list[str]  (e.g. ["G76厦蓉高速", "G15沈海高速"])
                - distance: int           (meters)
                - duration: int           (seconds)
                - tunnel_count: int
                - tunnel_distance: int
                - risk_warnings: list[str] (optional)
            vehicle_info: Vehicle parameters. Expected keys:
                - length: float (m)
                - width: float (m)
                - height: float (m)
                - weight: float (tons)
                - axis_weight: float (tons, optional)
                - axis_count: int (optional)
                - axis_loads: list[float] (optional)
                - axis_spacings: list[float] (optional)

        Returns:
            Structured assessment dict matching the target format
            (see Files/Dify_parameter/result.json).
        """
        route_name = route_data.get("route_description", "未知路线")
        route_id = route_data.get("id", "route_1")

        # ── 1. Bridge safety assessment ──
        amap_route_info = _build_amap_route_info(route_data)
        bridge_result = bridge_service.assess_route_safety(
            amap_route_info, vehicle_info
        )

        # ── 2. Construction / traffic event matching ──
        construction_result = _run_construction_match(route_data, amap_route_info)

        # ── 3. Dimension compliance check ──
        dimension_result = _assess_dimensions(vehicle_info, route_data)

        # ── 4. Compute composite score ──
        bridge_score, construction_score, dimension_score = _compute_scores(
            bridge_result, construction_result, dimension_result
        )
        total_score = round(bridge_score + construction_score + dimension_score, 1)

        # ── 5. Determine recommendation and risk level ──
        recommendation, risk_level = _determine_recommendation(total_score)

        # ── 6. Build key factors ──
        key_factors = _build_key_factors(
            bridge_result, construction_result, dimension_result, total_score
        )

        # ── 7. Traffic analysis ──
        traffic_analysis = _build_traffic_analysis(
            route_data, construction_result
        )

        # ── 8. Route compatibility ──
        route_compatibility = _build_route_compatibility(
            bridge_result, dimension_result, vehicle_info, route_data
        )

        # ── 9. Recommendations ──
        recommendations = _build_recommendations(
            bridge_result, construction_result, dimension_result,
            vehicle_info, route_data, recommendation
        )

        # ── 10. Metadata ──
        now = datetime.now()
        metadata = {
            "assessment_date": f"{now.year}年{now.month}月{now.day}日",
            "data_sources": [
                "福建省高速公路数据库",
                "施工信息库",
                "高德地图MCP",
            ],
            "confidence_level": _determine_confidence(bridge_result),
        }

        # ── 11. Cost estimation ──
        try:
            cost_estimate = cost_estimator.estimate(
                route_data=route_data,
                vehicle_info=vehicle_info,
            )
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            cost_estimate = {
                "total": 0,
                "breakdown": {},
                "warnings": [f"运费估算失败: {str(e)}"],
                "estimated_days": 0,
            }

        return {
            "route_id": route_id,
            "route_name": route_name,
            "overall_assessment": {
                "recommendation": recommendation,
                "risk_level": risk_level,
                "score": total_score,
                "key_factors": key_factors,
            },
            "traffic_analysis": traffic_analysis,
            "route_compatibility": route_compatibility,
            "recommendations": recommendations,
            "metadata": metadata,
            "cost_estimate": cost_estimate,
        }

    @staticmethod
    def compare_routes(
        routes: list[dict],
        vehicle_info: dict,
    ) -> dict:
        """Assess multiple routes and rank them.

        Args:
            routes: List of route_data dicts.
            vehicle_info: Vehicle parameters.

        Returns:
            {
                "ranked_routes": [...],  # Each route with its assessment
                "best_route_id": str,
                "comparison_summary": str,
            }
        """
        assessments = []
        for rt in routes:
            try:
                assessment = RouteAssessor.assess_route(rt, vehicle_info)
                cost_est = assessment.get("cost_estimate", {})
                assessments.append({
                    "route_id": assessment["route_id"],
                    "route_name": assessment["route_name"],
                    "score": assessment["overall_assessment"]["score"],
                    "recommendation": assessment["overall_assessment"]["recommendation"],
                    "risk_level": assessment["overall_assessment"]["risk_level"],
                    "time_minutes": rt.get("duration", 0) // 60,
                    "distance_km": round(rt.get("distance", 0) / 1000, 1),
                    "toll_cost": rt.get("toll_cost", 0),
                    "estimated_total_cost": cost_est.get("total", 0),
                    "estimated_days": cost_est.get("estimated_days", 0),
                    "assessment": assessment,
                })
            except Exception as e:
                logger.error(f"Failed to assess route {rt.get('id', '?')}: {e}")
                assessments.append({
                    "route_id": rt.get("id", "unknown"),
                    "route_name": rt.get("route_description", "未知路线"),
                    "error": str(e),
                })

        # Sort by score descending
        valid = [a for a in assessments if "score" in a]
        valid.sort(key=lambda a: a["score"], reverse=True)

        all_sorted = valid + [a for a in assessments if "error" in a]

        best_id = valid[0]["route_id"] if valid else None

        # Generate comparison summary
        if len(valid) >= 2:
            best = valid[0]
            worst = valid[-1]
            summary = (
                f"共评估 {len(assessments)} 条路线。"
                f"推荐路线 {best['route_id']}（{best['route_name']}），"
                f"评分 {best['score']}/10，"
                f"预计 {best['time_minutes']} 分钟，{best['distance_km']} 公里。"
            )
            if best["route_id"] != worst["route_id"]:
                summary += (
                    f" 相比最差路线 {worst['route_id']}（评分 {worst['score']}/10），"
                    f"得分差距 {best['score'] - worst['score']:.1f} 分。"
                )
        elif len(valid) == 1:
            summary = (
                f"仅评估 1 条路线。"
                f"路线 {valid[0]['route_id']}（{valid[0]['route_name']}），"
                f"评分 {valid[0]['score']}/10。"
            )
        else:
            summary = "所有路线评估失败。"

        return {
            "ranked_routes": all_sorted,
            "best_route_id": best_id,
            "comparison_summary": summary,
        }


# ── Internal helpers ──

def _build_amap_route_info(route_data: dict) -> dict:
    """Convert generic route_data into the format expected by bridge_service."""
    major_roads = route_data.get("major_roads", [])
    route_description = route_data.get("route_description", "")

    # Extract all expressway codes from both major_roads and route_description
    extracted_codes = []

    # 1. Try to extract highway codes from major_roads (e.g. "G76厦蓉高速" → "G76")
    for r in major_roads:
        m = re.search(r'([GS]\d{1,4})', r)
        if m:
            extracted_codes.append(m.group(1))

    # 2. Also parse route_description for expressway codes
    #    Format: "--G3京台高速--" or "--G1517莆炎高速--"
    #    The expressway name is between the code number and "高速"
    if route_description:
        for m in re.finditer(r'([GS]\d{1,4})[^\-\s]{1,8}高速', route_description):
            code = m.group(1)
            if code not in extracted_codes:
                extracted_codes.append(code)

    # 3. If we found expressway codes, use them as the primary major_roads
    #    for bridge assessment (the bridge DB only covers expressways)
    if extracted_codes:
        major_roads = extracted_codes

    return {
        "route_description": route_description,
        "major_roads": major_roads,
        "distance": route_data.get("distance", 0),
        "tunnel_count": route_data.get("tunnel_count", 0),
        "tunnel_distance": route_data.get("tunnel_distance", 0),
    }


def _run_construction_match(route_data: dict, amap_route_info: dict) -> dict:
    """Match construction events to the route's highway segments.

    Returns a dict with matched events and computed impacts.
    """
    try:
        # Extract highway codes from route data
        hw_codes = set()
        for road in amap_route_info.get("major_roads", []):
            m = re.search(r'([GS]\d{1,4})', road)
            if m:
                hw_codes.add(m.group(1))

        # Also extract from route_description
        desc = route_data.get("route_description", "")
        if desc:
            for m in re.finditer(r'([GS]\d{1,4})', desc):
                hw_codes.add(m.group(1))

        if not hw_codes:
            return {"matching_events": 0, "matches": [], "warnings": []}

        # Build K-range segments from junction_positions
        segments = []
        for hw in hw_codes:
            positions = query(
                """SELECT junction_name, k_value FROM junction_positions
                   WHERE highway_code = ? ORDER BY k_value""",
                (hw,)
            )
            if len(positions) >= 2:
                k_values = [p["k_value"] for p in positions]
                k_min = min(k_values)
                k_max = max(k_values)
                segments.append({
                    "highway_code": hw,
                    "k_from": k_min,
                    "k_to": k_max,
                })

        events = load_all_events()
        result = match_events_to_route(
            list(hw_codes),
            segments if segments else None,
            events,
        )
        return result
    except Exception as e:
        logger.error(f"Construction match failed: {e}")
        return {"matching_events": 0, "matches": [], "warnings": []}


def _assess_dimensions(vehicle_info: dict, route_data: dict) -> dict:
    """Check vehicle dimensions against route constraints.

    Returns:
        {
            "height_ok": bool,
            "width_ok": bool,
            "weight_ok": bool,
            "total_checkpoints": int,
            "height_passed": int,
            "weight_passed": int,
            "height_status": str,
            "weight_status": str,
            "warnings": list[str],
        }
    """
    height = vehicle_info.get("height", 4.0)
    width = vehicle_info.get("width", 2.55)
    weight = vehicle_info.get("total_weight", 49.0)

    # Estimate checkpoints: one per highway segment + one per tunnel
    # (simplified: use major_roads count + tunnel_count)
    major_roads = route_data.get("major_roads", [])
    tunnel_count = route_data.get("tunnel_count", 0)
    total_checkpoints = max(len(major_roads) + tunnel_count, 1)

    warnings = []

    # ── Height check ──
    # Standard expressway clearance: 5.0m
    # Tunnel typical clearance: 5.0m (some older tunnels may be 4.5m)
    height_limit = 5.0
    if height > 5.0:
        height_ok = False
        height_passed = 0
        warnings.append(
            f"车辆高度 {height}m 超过高速公路标准净空 {height_limit}m，"
            f"无法通过 {total_checkpoints}/{total_checkpoints} 个检查点"
        )
    elif height > 4.8:
        height_ok = True
        # Borderline: some older tunnels may be restrictive
        height_passed = total_checkpoints - max(tunnel_count // 3, 0)
        warnings.append(
            f"车辆高度 {height}m 接近净空上限，部分老旧隧道可能受限"
        )
    else:
        height_ok = True
        height_passed = total_checkpoints

    # ── Width check ──
    # Standard lane width: 3.75m
    # Oversized cargo lanes: up to 5.0m (with permits)
    if width > 5.0:
        width_ok = False
        warnings.append(
            f"车辆宽度 {width}m 严重超标，无法在高速公路上通行"
        )
    elif width > 3.75:
        width_ok = True  # Passable with special permit and lane occupation
        warnings.append(
            f"车辆宽度 {width}m 超过标准车道宽度 3.75m，需占用多车道并办理特批"
        )
    elif width > 3.0:
        width_ok = True
        warnings.append(
            f"车辆宽度 {width}m，需确认收费站超宽车道可用性"
        )
    else:
        width_ok = True

    # ── Weight check ──
    # Note: Structural weight safety is handled by the bridge assessment.
    # This check is a regulatory pre-check for road/bridge weight limits.
    # Standard limit: 49 tons (6-axis). Special permits allow up to ~200 tons.
    weight_limit = 55.0  # tons (standard + special permit threshold)
    if weight > 100.0:
        # Severely overweight: almost certainly exceeds bridge capacity
        weight_ok = False
        weight_passed = 0
        warnings.append(
            f"车辆总重 {weight}吨 远超常规限重，需逐桥评估通行能力"
        )
    elif weight > 55.0:
        # Overweight but potentially passable with permits + bridge assessment
        weight_ok = True
        weight_passed = total_checkpoints
        warnings.append(
            f"车辆总重 {weight}吨 超过标准限重 55吨，需办理超限运输许可并逐桥评估"
        )
    elif weight > 49.0:
        weight_ok = True
        weight_passed = total_checkpoints
        warnings.append(
            f"车辆总重 {weight}吨 超过标准限重 49吨，需办理超限运输许可"
        )
    else:
        weight_ok = True
        weight_passed = total_checkpoints

    all_ok = height_ok and width_ok and weight_ok

    if all_ok and not warnings:
        dimension_status = "完全符合"
    elif all_ok:
        dimension_status = "基本符合（存在注意事项）"
    else:
        dimension_status = "不符合"

    # Status strings
    if height_ok:
        height_status = f"通过 {height_passed}/{total_checkpoints} 个检查点"
    else:
        height_status = f"未通过（车辆高度 {height}m 超过限高 {height_limit}m）"

    if weight_ok:
        weight_status = f"符合 {weight_passed}/{total_checkpoints} 个路段要求"
    else:
        weight_status = f"不符合（车辆总重 {weight}吨 远超限重，无法通行）"

    return {
        "height_ok": height_ok,
        "width_ok": width_ok,
        "weight_ok": weight_ok,
        "all_ok": all_ok,
        "total_checkpoints": total_checkpoints,
        "height_passed": height_passed,
        "height_limit": height_limit,
        "vehicle_height": height,
        "weight_limit": weight_limit,
        "vehicle_weight": weight,
        "height_status": height_status,
        "weight_status": weight_status,
        "dimension_status": dimension_status,
        "warnings": warnings,
    }


def _compute_scores(
    bridge_result: dict,
    construction_result: dict,
    dimension_result: dict,
) -> tuple:
    """Compute 0-4, 0-3, 0-3 scores for the three dimensions.

    Returns (bridge_score, construction_score, dimension_score).
    """
    # ── Bridge score (0-4) ──
    risky_count = bridge_result.get("risky_bridges", 0)
    max_ratio = bridge_result.get("max_effect_ratio", 0)
    total_bridges = bridge_result.get("total_bridges_on_route", 0)
    bridges_evaluated = bridge_result.get("bridges_evaluated", 0)
    route_restrictions = bridge_result.get("route_level_restrictions", {})
    reinforcement_needed = route_restrictions.get("reinforcement_needed", False)
    grades_summary = route_restrictions.get("bridge_grades_summary", {})

    if total_bridges == 0 or bridges_evaluated == 0:
        # No bridge data available: cannot assess, give partial score
        bridge_score = 2  # Neutral/unknown
    elif reinforcement_needed:
        # Any bridge needing reinforcement → severe risk
        bridge_score = 0
    elif risky_count > 1 or max_ratio >= 1.0:
        # Multiple risky bridges or ratio >= 1.0
        bridge_score = 1  # Slightly better than SCORE_BRIDGE_MANY_RISKY for conditional pass
    elif risky_count == 0 and max_ratio < 0.6:
        bridge_score = SCORE_BRIDGE_ALL_PASS  # 4
    elif risky_count == 0 and max_ratio < 0.8:
        bridge_score = 3  # Near-perfect
    elif risky_count <= 1 or max_ratio < 1.0:
        bridge_score = SCORE_BRIDGE_ONE_RISKY  # 2
    else:
        bridge_score = SCORE_BRIDGE_MANY_RISKY  # 0

    # ── Construction score (0-3) ──
    match_count = construction_result.get("matching_events", 0)

    if match_count == 0:
        construction_score = SCORE_CONSTRUCTION_NONE  # 3
    elif match_count <= 2:
        construction_score = SCORE_CONSTRUCTION_SOME  # 1
    else:
        construction_score = SCORE_CONSTRUCTION_MANY  # 0

    # ── Dimension score (0-3) ──
    if dimension_result.get("all_ok", False):
        if not dimension_result.get("warnings"):
            dimension_score = SCORE_DIMENSION_ALL_PASS  # 3
        else:
            dimension_score = SCORE_DIMENSION_BORDERLINE  # 1
    else:
        dimension_score = SCORE_DIMENSION_FAIL  # 0

    return bridge_score, construction_score, dimension_score


def _determine_recommendation(total_score: float) -> tuple:
    """Map composite score to recommendation and risk level.

    Returns (recommendation_str, risk_level_str).
    """
    if total_score >= 7:
        recommendation = "推荐"
    elif total_score >= 5:
        recommendation = "谨慎"
    else:
        recommendation = "不推荐"

    if total_score >= 8:
        risk_level = "低"
    elif total_score >= 6:
        risk_level = "中"
    elif total_score >= 4:
        risk_level = "高"
    else:
        risk_level = "极高"

    return recommendation, risk_level


def _build_key_factors(
    bridge_result: dict,
    construction_result: dict,
    dimension_result: dict,
    total_score: float,
) -> list[str]:
    """Generate human-readable key factors summarizing the assessment."""
    factors = []

    risky_count = bridge_result.get("risky_bridges", 0)
    total_bridges = bridge_result.get("total_bridges_on_route", 0)
    bridges_evaluated = bridge_result.get("bridges_evaluated", 0)
    route_restrictions = bridge_result.get("route_level_restrictions", {})
    reinforcement_needed = route_restrictions.get("reinforcement_needed", False)
    escort_required = route_restrictions.get("escort_required", False)
    route_max_speed = route_restrictions.get("max_speed_kmh")

    if reinforcement_needed:
        factors.append("桥梁需要加固后方可通行")
    elif total_bridges == 0 or bridges_evaluated == 0:
        factors.append("桥梁数据未覆盖该路线（无法匹配到已知高速公路桥梁）")
    elif risky_count == 0 and total_bridges > 0:
        if route_max_speed and route_max_speed <= 40:
            factors.append(f"桥梁安全可控（建议限速≤{route_max_speed}km/h）")
        else:
            factors.append("桥梁安全系数较高")
    elif risky_count <= 1:
        if escort_required:
            factors.append("部分桥梁需护送通行")
        else:
            factors.append("部分桥梁需重点关注")
    else:
        factors.append("多座桥梁存在通行风险")

    match_count = construction_result.get("matching_events", 0)
    if match_count == 0:
        factors.append("施工影响最小")
    elif match_count <= 2:
        factors.append("存在少量施工影响")
    else:
        factors.append("施工路段较多需注意")

    if dimension_result.get("all_ok", False):
        if not dimension_result.get("warnings"):
            factors.append("车辆尺寸完全达标")
        else:
            factors.append("车辆尺寸基本合规（需注意个别限制）")
    else:
        factors.append("车辆尺寸不符合通行要求")

    # Additional factors from route data
    if total_score >= 7:
        factors.append("通行时间最短")

    return factors[:5]  # Cap at 5 factors


def _build_traffic_analysis(
    route_data: dict,
    construction_result: dict,
) -> dict:
    """Build traffic analysis section."""
    duration_sec = route_data.get("duration", 0)
    hours = duration_sec // 3600
    minutes = (duration_sec % 3600) // 60
    if hours > 0:
        estimated_time = f"约{hours}小时{minutes}分钟"
    else:
        estimated_time = f"约{minutes}分钟"

    # Extract construction impacts
    construction_impacts = []
    total_delay = 0

    matches = construction_result.get("matches", [])
    for m_item in matches:
        evt = m_item["event"]
        overlap_pct = m_item.get("overlap_pct", 0)

        # Determine impact level
        if overlap_pct > 50:
            impact_level = "严重"
            delay = 30
        elif overlap_pct > 20:
            impact_level = "中等"
            delay = 15
        else:
            impact_level = "轻微"
            delay = 5

        k_str_start = f"K{evt.k_start:.0f}+{int((evt.k_start%1)*1000):03d}"
        k_str_end = f"K{evt.k_end:.0f}+{int((evt.k_end%1)*1000):03d}"

        construction_impacts.append({
            "location": f"{evt.highway_code}{evt.highway_name}{k_str_start}-{k_str_end}处",
            "impact_level": impact_level,
            "lane_occupancy": evt.description or "主车道、应急车道",
            "delay_minutes": delay,
        })
        total_delay += delay

    # Traffic incidents (from matches that are incidents, not construction)
    traffic_incidents = []
    warnings_text = construction_result.get("warnings", [])

    # Calculate recommended time window
    recommended_time_window = "上午8:00-11:00"
    if total_delay > 0:
        recommended_time_window += "（避开施工高峰期）"

    return {
        "estimated_time": estimated_time,
        "construction_impacts": construction_impacts,
        "traffic_incidents": traffic_incidents,
        "total_delay": total_delay,
        "recommended_time_window": recommended_time_window,
    }


def _build_route_compatibility(
    bridge_result: dict,
    dimension_result: dict,
    vehicle_info: dict,
    route_data: dict,
) -> dict:
    """Build route compatibility section (dimension_check + structural_safety)."""
    # Dimension check
    dimension_check = {
        "height_limit": dimension_result.get("height_limit", 5.0),
        "vehicle_height": dimension_result.get("vehicle_height", 0),
        "height_status": dimension_result.get("height_status", ""),
        "weight_limit": dimension_result.get("weight_limit", 55.0),
        "vehicle_weight": dimension_result.get("vehicle_weight", 0),
        "weight_status": dimension_result.get("weight_status", ""),
    }

    # Structural safety
    bridge_details = bridge_result.get("bridge_details", [])
    ratios = [d.get("max_ratio", 0) for d in bridge_details if "max_ratio" in d]
    min_ratio = round(min(ratios), 2) if ratios else 0.0
    max_moment_ratio = round(max(ratios), 2) if ratios else 0.0

    total_bridges = bridge_result.get("total_bridges_on_route", 0)
    risky_count = bridge_result.get("risky_bridges", 0)
    route_restrictions = bridge_result.get("route_level_restrictions", {})

    # Extract worst-case passability details
    escort_required = route_restrictions.get("escort_required", False)
    reinforcement_needed = route_restrictions.get("reinforcement_needed", False)
    route_max_speed = route_restrictions.get("max_speed_kmh")
    grades_summary = route_restrictions.get("bridge_grades_summary", {})

    # Determine safety assessment string
    if total_bridges == 0:
        safety_assessment = "桥梁数据未覆盖（无法评估桥梁安全性）"
    elif reinforcement_needed:
        safety_assessment = "通行风险极高（需桥梁加固）"
    elif escort_required:
        safety_assessment = f"条件通行（需护送，限速≤{route_max_speed}km/h）" if route_max_speed else "条件通行（需护送）"
    elif risky_count > 0:
        safety_assessment = f"限速通行（限速≤{route_max_speed}km/h）" if route_max_speed else "限速通行"
    elif max_moment_ratio >= 0.8:
        safety_assessment = "基本安全（建议限速）"
    elif max_moment_ratio >= 0.6:
        safety_assessment = "安全通行"
    else:
        safety_assessment = "完全安全通行"

    structural_safety = {
        "total_bridges": total_bridges,
        "high_risk_bridges": risky_count,
        "min_effect_ratio": min_ratio,
        "max_moment_ratio": max_moment_ratio,
        "safety_threshold": 0.8,
        "safety_assessment": safety_assessment,
        "route_max_speed_kmh": route_max_speed,
        "escort_required": escort_required,
        "reinforcement_needed": reinforcement_needed,
        "bridge_grades_summary": grades_summary,
        "bridge_details": bridge_details,
    }

    compliance_status = dimension_result.get("dimension_status", "未知")

    return {
        "dimension_check": dimension_check,
        "structural_safety": structural_safety,
        "compliance_status": compliance_status,
    }


def _build_recommendations(
    bridge_result: dict,
    construction_result: dict,
    dimension_result: dict,
    vehicle_info: dict,
    route_data: dict,
    recommendation: str,
) -> dict:
    """Build user and approver recommendations."""
    for_user = []
    for_approver_special = []
    risk_notes_parts = []

    # User recommendations
    match_count = construction_result.get("matching_events", 0)
    if match_count > 0:
        for_user.append("通过施工路段时保持安全车距")
        for_user.append("控制车速在60km/h以下")
        for_user.append("避开施工高峰期")

    if dimension_result.get("warnings"):
        for_user.append("注意沿途限高限宽标志")
        if vehicle_info.get("width", 0) > 3.75:
            for_user.append("通过收费站时选择超宽车道")

    risky_count = bridge_result.get("risky_bridges", 0)
    route_restrictions = bridge_result.get("route_level_restrictions", {})
    route_max_speed = route_restrictions.get("max_speed_kmh")
    escort_required = route_restrictions.get("escort_required", False)
    reinforcement_needed = route_restrictions.get("reinforcement_needed", False)

    if risky_count > 0:
        if route_max_speed is not None and route_max_speed > 0:
            for_user.append(f"通过桥梁时严格限速≤{route_max_speed}km/h")
        else:
            for_user.append("通过桥梁时减速慢行")
        for_user.append("避免在桥梁上停车或紧急制动")
        if escort_required:
            for_user.append("需安排护送车辆全程陪同")
        if reinforcement_needed:
            for_user.append("部分桥梁需要临时加固后方可通行")
    elif bridge_result.get("max_effect_ratio", 0) >= 0.8:
        for_user.append(f"部分桥梁效应比值较高，建议限速≤40km/h通过")
    elif bridge_result.get("max_effect_ratio", 0) >= 0.6:
        for_user.append("部分桥梁效应比值偏高，注意控制车速")

    tunnel_count = route_data.get("tunnel_count", 0)
    if tunnel_count > 5:
        for_user.append("隧道较多，注意开启车灯并保持安全车距")

    # General advice
    for_user.append("出发前检查车辆状况（刹车、轮胎、灯光）")

    # Approver recommendations
    if recommendation == "推荐":
        approval_decision = "建议批准"
    elif recommendation == "谨慎":
        approval_decision = "有条件批准"
    else:
        approval_decision = "不建议批准"

    # Special conditions
    if match_count > 0:
        for_approver_special.append("通过施工路段时需减速慢行")
    if dimension_result.get("warnings"):
        for_approver_special.append("需确认路线所有检查点限高限宽满足车辆尺寸")
    if reinforcement_needed:
        for_approver_special.append("至少1座桥梁需要加固或临时支撑后方可通行，建议重新规划路线")
    elif risky_count > 0:
        if escort_required:
            for_approver_special.append("高风险桥梁通行需安排护送车辆，限速≤20km/h")
        else:
            for_approver_special.append("需对高风险桥梁进行现场勘察并确认通行条件")
    if vehicle_info.get("total_weight", 0) > 49.0:
        for_approver_special.append("需办理超限运输许可证")

    for_approver_special.append("出发前关注天气预报")
    for_approver_special.append("准备应急预案（备用路线、维修联系方式）")

    # Risk notes
    if risky_count > 0:
        grades_summary = route_restrictions.get("bridge_grades_summary", {})
        grade_desc = "、".join(f"{v}座{g}" for g, v in grades_summary.items() if g != "未评估")
        if grade_desc:
            risk_notes_parts.append(f"桥梁评级分布：{grade_desc}")
        else:
            risk_notes_parts.append(f"有{risky_count}座桥梁存在通行风险")
    if match_count > 0:
        risk_notes_parts.append(f"路线经过{match_count}处施工/事件路段")
    if dimension_result.get("warnings"):
        risk_notes_parts.append("车辆尺寸接近限值需要关注")

    if not risk_notes_parts:
        risk_notes = "路线相对直接，桥梁安全系数较高，风险可控"
    else:
        risk_notes = "；".join(risk_notes_parts)
        if recommendation == "推荐":
            risk_notes += "，但风险可控"

    return {
        "for_user": for_user,
        "for_approver": {
            "approval_decision": approval_decision,
            "special_conditions": for_approver_special,
            "risk_notes": risk_notes,
        },
    }


def _determine_confidence(bridge_result: dict) -> str:
    """Determine confidence level based on data completeness."""
    bridges_evaluated = bridge_result.get("bridges_evaluated", 0)
    total_bridges = bridge_result.get("total_bridges_on_route", 0)

    if total_bridges == 0:
        return "低"
    if bridges_evaluated >= total_bridges:
        return "高"
    if bridges_evaluated >= total_bridges * 0.7:
        return "中"
    return "低"


# Singleton
route_assessor = RouteAssessor()
