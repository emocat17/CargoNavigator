"""
Bridge Safety Assessment Service.

Unifies:
- Bridge effect calculation (荷载效应对比法)
- Highway network path finding
- Route-level bridge risk assessment

This is THE core service for answering "这条路安全吗？"
"""
import logging
from typing import Optional

from app.services.bridge_effect_calculator import (
    calculate_bridge_effect,
    find_bridges_on_road_section,
    evaluate_route_bridges,
    _parse_station_k,
)
from app.services.highway_network import (
    find_all_paths,
    find_nearest_junction,
    map_amap_route_to_junctions,
    haversine,
    get_highway_info,
)
from app.bridge_db import query, query_one

logger = logging.getLogger(__name__)


class BridgeService:
    """Bridge safety assessment for oversized cargo transport routes."""

    @staticmethod
    def assess_route_safety(
        amap_route_info: dict,
        vehicle_info: dict,
    ) -> dict:
        """Full route safety assessment.

        Args:
            amap_route_info: Route data from Amap API (processed by routes.py)
                {
                    "route_description": "三明--G1517莆炎高速--港后枢纽--G15沈海高速--...",
                    "major_roads": ["G1517莆炎高速", "G15沈海高速", "S53渔平支线"],
                    "distance": 285000,  # meters
                    "tunnel_count": 53,
                }
            vehicle_info: Vehicle parameters
                {
                    "length": 24.0,   # meters
                    "width": 4.9,     # meters
                    "height": 4.7,    # meters
                    "weight": 150.0,  # tons (total)
                    "axis_weight": 18.0,  # max axis weight
                    "axis_count": 8,
                    "axis_loads": [10, 10, 10, 17.98, 17.98, 17.98, 17.98, 17.98],  # optional
                    "axis_spacings": [3.2, 1.4, 7.0, 1.45, 1.45, 1.45, 1.45],       # optional
                }

        Returns:
            {
                "overall_safe": bool,
                "risk_level": "低/中/高/极高",
                "total_bridges_on_route": int,
                "bridges_evaluated": int,
                "passable_bridges": int,
                "risky_bridges": int,
                "max_effect_ratio": float,
                "bridge_details": [...],
                "warnings": [...],
                "recommendations": [...],
            }
        """
        warnings = []
        recommendations = []
        bridge_details = []

        # ── 1. Extract highway segments from Amap route ──
        major_roads = amap_route_info.get("major_roads", [])
        route_desc = amap_route_info.get("route_description", "")

        # Try to map route to highway network
        highway_segments = map_amap_route_to_junctions(route_desc, major_roads)

        if not highway_segments:
            return {
                "overall_safe": True,
                "risk_level": "未知",
                "total_bridges_on_route": 0,
                "bridges_evaluated": 0,
                "passable_bridges": 0,
                "risky_bridges": 0,
                "max_effect_ratio": 0.0,
                "bridge_details": [],
                "warnings": ["无法将路线映射到高速公路网络，桥梁评估未执行"],
                "recommendations": ["建议手动核实沿途桥梁的通行能力"],
            }

        # ── 2. Build axle load config from vehicle info ──
        axle_loads = _build_axle_config(vehicle_info)
        if not axle_loads:
            return {
                "overall_safe": True,
                "risk_level": "未知",
                "total_bridges_on_route": 0,
                "bridges_evaluated": 0,
                "passable_bridges": 0,
                "risky_bridges": 0,
                "max_effect_ratio": 0.0,
                "bridge_details": [],
                "warnings": ["缺少车辆轴重/轴距数据，无法评估桥梁安全性"],
                "recommendations": ["请提供轴重分布和轴距信息以进行精确桥梁评估"],
            }

        # ── 3. Find bridges on each highway segment ──
        all_bridges = []
        seen_stations = set()

        for seg in highway_segments:
            hw = seg["highway_code"]
            if not hw:
                continue
            # Find all bridges on this highway
            bridges = query(
                """SELECT id, station, bridge_type, span, highway_code,
                          pos_moment_design, neg_moment_design, shear_design,
                          frequency, data_folder
                   FROM bridges WHERE highway_code = ?""",
                (hw,)
            )
            for b in bridges:
                key = (b["station"], b["highway_code"])
                if key not in seen_stations:
                    seen_stations.add(key)
                    all_bridges.append(dict(b))

        if not all_bridges:
            return {
                "overall_safe": True,
                "risk_level": "低",
                "total_bridges_on_route": 0,
                "bridges_evaluated": 0,
                "passable_bridges": 0,
                "risky_bridges": 0,
                "max_effect_ratio": 0.0,
                "bridge_details": [],
                "warnings": ["该路线涉及的高速公路暂无桥梁数据"],
                "recommendations": ["建议现场勘察确认桥梁通行条件"],
            }

        # ── 4. Calculate effect for each bridge ──
        loads_ton = axle_loads["loads_ton"]
        spacings = axle_loads["spacings"]

        passable = 0
        risky = 0
        max_ratio = 0.0
        route_max_speed = None  # worst-case speed limit
        route_escort_required = False
        route_reinforcement_needed = False
        bridge_grades_summary = {}  # grade → count

        for b in all_bridges:
            result = calculate_bridge_effect(
                loads_ton, spacings,
                b["station"], b.get("highway_code")
            )
            if "error" in result:
                bridge_details.append({
                    "station": b["station"],
                    "type": b.get("bridge_type", "未知"),
                    "highway": b.get("highway_code", ""),
                    "status": "未评估",
                    "reason": result["error"],
                    "passability": {
                        "grade": "未评估",
                        "max_speed_kmh": None,
                        "lane_restriction": "unknown",
                        "escort_required": False,
                        "reinforcement_needed": False,
                        "bridge_specific_notes": "无法计算：缺少桥梁数据",
                    },
                })
                passable += 1  # err on the side of caution
            else:
                is_ok = result["is_passable"]
                ratio = result["max_ratio"]
                max_ratio = max(max_ratio, ratio)
                pass_info = result.get("passability", {})

                # Track grade counts
                grade = pass_info.get("grade", "未知")
                bridge_grades_summary[grade] = bridge_grades_summary.get(grade, 0) + 1

                # Aggregate route-level restrictions (worst case)
                speed = pass_info.get("max_speed_kmh")
                if speed is not None:
                    if route_max_speed is None or speed < route_max_speed:
                        route_max_speed = speed
                if pass_info.get("escort_required"):
                    route_escort_required = True
                if pass_info.get("reinforcement_needed"):
                    route_reinforcement_needed = True

                detail = {
                    "station": result["station"],
                    "type": result["bridge_type"],
                    "highway": result["highway_code"],
                    "highway_name": result.get("highway_name", ""),
                    "pos_moment_ratio": result["pos_moment_ratio"],
                    "neg_moment_ratio": result["neg_moment_ratio"],
                    "shear_ratio": result["shear_ratio"],
                    "max_ratio": ratio,
                    "damping_factor": result["damping_factor"],
                    "safe": is_ok,
                    "passability": pass_info,
                }
                bridge_details.append(detail)

                if is_ok:
                    passable += 1
                else:
                    risky += 1
                    grade_info = pass_info.get("grade", "存在风险")
                    speed_info = f"，限速≤{speed}km/h" if speed else ""
                    warnings.append(
                        f"[!] {result['station']} {result['bridge_type']} ({result['highway_code']}): "
                        f"最大效应比值 {ratio:.3f}，评级：{grade_info}{speed_info}"
                    )

        # ── 5. Determine risk level ──
        if route_reinforcement_needed or max_ratio >= 1.2:
            risk_level = "极高"
        elif risky > 0:
            risk_level = "高"
        elif max_ratio >= 0.8:
            risk_level = "中"
        else:
            risk_level = "低"

        # ── 6. Space passability check ──
        space_warnings = _check_space_passability(vehicle_info, amap_route_info)
        warnings.extend(space_warnings)

        # ── 7. Build route-level restrictions ──
        route_level_restrictions = {
            "max_speed_kmh": route_max_speed,
            "escort_required": route_escort_required,
            "reinforcement_needed": route_reinforcement_needed,
            "bridge_grades_summary": bridge_grades_summary,
        }

        # ── 8. Generate recommendations ──
        if route_reinforcement_needed:
            recommendations.append(
                f"发现 {risky} 座桥梁需要加固或限行，强烈建议重新规划路线"
            )
        elif risky > 0:
            if route_escort_required:
                recommendations.append(
                    f"发现 {risky} 座桥梁效应比值超标，通行需护送车辆陪同，限速≤{route_max_speed}km/h"
                )
            else:
                recommendations.append(
                    f"发现 {risky} 座桥梁效应比值超标，建议限速≤{route_max_speed}km/h"
                )
        if 0.8 <= max_ratio < 1.0:
            recommendations.append(
                f"部分桥梁效应比值接近临界值(≥0.8)，建议通过时减速慢行(≤40km/h)"
            )
        if passable > 0 and risky == 0:
            bridge_count = bridge_grades_summary.get("安全通行", 0) + bridge_grades_summary.get("正常通行", 0) + bridge_grades_summary.get("建议限速", 0)
            recommendations.append(
                f"路线经过 {passable} 座桥梁，经评估均可安全通行"
            )
        if route_escort_required:
            recommendations.append(
                "通行时需要护送车辆全程陪同"
            )

        tunnel_count = amap_route_info.get("tunnel_count", 0)
        if tunnel_count > 10:
            recommendations.append(
                f"路线包含 {tunnel_count} 座隧道，建议核实所有隧道的限高/限宽是否满足车辆尺寸"
            )

        return {
            "overall_safe": risky == 0 and not space_warnings,
            "risk_level": risk_level,
            "total_bridges_on_route": len(all_bridges),
            "bridges_evaluated": len(bridge_details),
            "passable_bridges": passable,
            "risky_bridges": risky,
            "max_effect_ratio": round(max_ratio, 4),
            "bridge_details": bridge_details[:20],  # top 20 for context
            "route_highways": [s.get("highway_code", "") for s in highway_segments],
            "route_level_restrictions": route_level_restrictions,
            "warnings": warnings,
            "recommendations": recommendations,
        }


def _build_axle_config(vehicle_info: dict) -> Optional[dict]:
    """Build axle load configuration from vehicle info.

    If axis_loads/spacings are provided, use them.
    Otherwise, estimate from basic parameters.
    """
    if "axis_loads" in vehicle_info and "axis_spacings" in vehicle_info:
        return {
            "loads_ton": vehicle_info["axis_loads"],
            "spacings": vehicle_info["axis_spacings"],
        }

    # Estimate from basic params
    total_weight = vehicle_info.get("total_weight", 49.0)  # tons
    axis_count = vehicle_info.get("axis_count", 6)
    max_axis_weight = vehicle_info.get("axis_weight", 10.0)

    if axis_count <= 0:
        return None

    # Simple uniform distribution
    avg_load = total_weight / axis_count
    loads = [avg_load] * axis_count

    # Estimate spacings: typical trailer axle spacing
    if axis_count <= 3:
        spacings = [3.5] * (axis_count - 1)
    elif axis_count <= 6:
        spacings = [3.2, 1.4] + [1.45] * (axis_count - 2)
    else:
        spacings = [3.2, 1.4, 7.0] + [1.45] * (axis_count - 3)

    return {
        "loads_ton": loads[:axis_count],
        "spacings": spacings[:axis_count - 1] if axis_count > 1 else [],
    }


def _check_space_passability(vehicle_info: dict, route_info: dict) -> list[str]:
    """Check space passability based on vehicle dimensions.

    Per 《公路大件运输安全通行评价技术规范》:
    - Height: must clear all bridges and tunnels (typically 5.0m for expressways)
    - Width: must fit within lane width (typically 3.75m per lane)
    - Turning radius: must navigate interchange ramps
    """
    warnings = []

    height = vehicle_info.get("height", 4.0)
    width = vehicle_info.get("width", 2.55)

    # Standard expressway clearance is 5.0m
    if height > 5.0:
        warnings.append(f"[!] 车辆高度 {height}m 超过高速公路标准净空 5.0m，需确认沿途无低矮设施")
    elif height > 4.5:
        warnings.append(f"车辆高度 {height}m，接近标准净空上限，建议核实隧道/天桥限高")

    # Lane width check
    if width > 3.75:
        warnings.append(f"[!] 车辆宽度 {width}m 超过标准车道宽度 3.75m，需占用多车道或办理特殊通行许可")
    elif width > 3.0:
        warnings.append(f"车辆宽度 {width}m，需注意收费站超宽车道可用性")

    return warnings


# Singleton
bridge_service = BridgeService()
