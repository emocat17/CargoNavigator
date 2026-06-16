"""
Digital Road Survey Checklist Generator.

Generates a prioritized pre-trip road survey checklist for oversized cargo transport.
Surveyors must physically check the route for clearance issues before departure.

Data sources (all existing in the system):
- Bridge DB: bridges table with station桩号, bridge_type, span, highway_code
- Junction Positions: k_values for each junction on each highway
- Space Checker: standard clearances (5.0m height, 3.75m lane width, 15m turning radius)
- Vehicle Classifier: A-E grade rating
"""

import logging
import re
from typing import Optional

from app.bridge_db import query
from app.services.space_checker import (
    STANDARD_CLEARANCE_HEIGHT,
    STANDARD_LANE_WIDTH,
    DEFAULT_MIN_TURNING_RADIUS,
    check_height,
    check_width,
    check_turning_radius,
)
from app.services.vehicle_classifier import classify_combined

logger = logging.getLogger(__name__)

# ── Priority definitions ──
PRIORITY_CRITICAL = "CRITICAL"    # Must check - effect_ratio > 0.9 or clearance fails
PRIORITY_HIGH = "HIGH"            # Should check - effect_ratio 0.7-0.9 or marginal clearance
PRIORITY_MEDIUM = "MEDIUM"        # Check if time permits
PRIORITY_LOW = "LOW"              # Low priority

# ── Equipment ──
SURVEY_EQUIPMENT = [
    "激光测距仪",
    "GPS定位仪",
    "相机",
    "测量卷尺(50m)",
    "对讲机",
    "安全警示服",
    "记录表格/平板电脑",
]

# ── Overhead obstacle types ──
OVERHEAD_OBSTACLE_TYPES = [
    "ETC门架",
    "龙门架标志牌",
    "跨线天桥",
    "高压电力线",
    "通信线缆",
    "隧道入口限高标志",
]


def _parse_station_to_km(station: str) -> float:
    """Parse a station桩号 string like 'k0+15' to a K-value float.

    'k0+15' -> 0.015  (km portion: 0, meter portion: 15)
    'k395+500' -> 395.5
    """
    if not station:
        return 0.0
    station = station.lower().replace("k", "").strip()
    parts = station.split("+")
    try:
        km = float(parts[0]) if parts[0] else 0.0
        m = float(parts[1]) / 1000.0 if len(parts) > 1 and parts[1] else 0.0
        return km + m
    except (ValueError, IndexError):
        return 0.0


def _station_sort_key(bridge: dict) -> float:
    """Sort key for bridges by station桩号 position."""
    return _parse_station_to_km(bridge.get("station", "k0+0"))


class RoadSurveyor:
    """Digital Road Survey Checklist Generator.

    Generates a detailed pre-trip road survey checklist for oversized cargo
    transport based on the planned route, vehicle dimensions, and bridge
    assessment data.
    """

    @staticmethod
    def generate_checklist(
        route_data: dict,
        vehicle_info: dict,
        bridge_assessment: dict = None,
    ) -> dict:
        """Generate a prioritized survey checklist.

        Args:
            route_data: Route information with keys:
                - route_description: str (e.g. "G1517莆炎高速(36km→395km) → G15沈海高速...")
                - major_roads: list[str] (highway road names)
                - distance: int (meters)
                - duration: int (seconds)
                - tunnel_count: int
                - tunnel_distance: int
            vehicle_info: Vehicle parameters with keys:
                - length: float (meters)
                - width: float (meters)
                - height: float (meters)
                - total_weight: float (tons)
                - axis_weight: float (tons, optional)
                - axis_count: int (optional)
            bridge_assessment: Optional pre-computed bridge assessment result
                from bridge_service.assess_route_safety(). If provided,
                effect_ratios are used for bridge risk prioritization.

        Returns:
            Structured survey checklist dict (see module docstring).
        """
        route_summary = route_data.get("route_description", "未知路线")
        major_roads = route_data.get("major_roads", [])

        # Extract highway codes from route data
        highway_codes = _extract_highway_codes(route_data, major_roads)

        # Vehicle dimensions
        length = float(vehicle_info.get("length", 17))
        width = float(vehicle_info.get("width", 2.55))
        height = float(vehicle_info.get("height", 4.0))
        total_weight = float(vehicle_info.get("total_weight", 49))

        # Classify vehicle
        vehicle_classification = classify_combined(vehicle_info)

        # ── 1. Bridge checklist ──
        bridge_items = _build_bridge_checklist(
            highway_codes, bridge_assessment
        )

        # ── 2. Tunnel checklist ──
        tunnel_items = _build_tunnel_checklist(
            route_data, highway_codes, height
        )

        # ── 3. Toll station checklist ──
        toll_items = _build_toll_station_checklist(
            highway_codes, width
        )

        # ── 4. Ramp (interchange) checklist ──
        ramp_items = _build_ramp_checklist(
            highway_codes, length
        )

        # ── 5. Overhead obstacle checklist ──
        overhead_items = _build_overhead_checklist(
            highway_codes, height
        )

        # ── Aggregate ──
        categories = {
            "bridges": bridge_items,
            "tunnels": tunnel_items,
            "toll_stations": toll_items,
            "ramps": ramp_items,
            "overhead_obstacles": overhead_items,
        }

        # Count totals
        total_check_points = sum(
            c.get("total", 0) for c in categories.values()
        )
        total_critical = sum(
            c.get("critical", 0) for c in categories.values()
        )

        # ── Suggested survey route (ordered by position) ──
        suggested_route = _build_suggested_route(categories)

        # ── Estimated survey time ──
        estimated_hours = _estimate_survey_time(
            total_check_points, bridge_items, tunnel_items
        )

        # ── Required equipment ──
        required_equipment = _determine_equipment(
            height, width, total_weight, bridge_items
        )

        return {
            "route_summary": route_summary,
            "total_check_points": total_check_points,
            "critical_points": total_critical,
            "vehicle_classification": vehicle_classification,
            "categories": categories,
            "suggested_survey_route": suggested_route,
            "estimated_survey_time_hours": estimated_hours,
            "required_equipment": required_equipment,
        }


# ── Internal helpers ──

def _extract_highway_codes(route_data: dict, major_roads: list[str]) -> list[str]:
    """Extract distinct highway codes from route data."""
    codes = set()
    desc = route_data.get("route_description", "")

    # From major_roads
    for road in major_roads:
        for m in re.finditer(r'([GS]\d{1,4})', road):
            codes.add(m.group(1))

    # From route_description
    if desc:
        for m in re.finditer(r'([GS]\d{1,4})', desc):
            codes.add(m.group(1))

    return list(codes) if codes else []


def _build_bridge_checklist(
    highway_codes: list[str],
    bridge_assessment: dict = None,
) -> dict:
    """Build bridge survey checklist sorted by risk.

    Scans the bridge DB for all bridges on the route's highways.
    Uses effect_ratio from bridge_assessment if available to prioritize.
    """
    items = []
    critical = 0

    if not highway_codes:
        return {"total": 0, "critical": 0, "items": []}

    # Query all bridges on these highways
    all_bridges = []
    for hw in highway_codes:
        bridges = query(
            """SELECT id, station, bridge_type, span, highway_code
               FROM bridges WHERE highway_code = ?""",
            (hw,)
        )
        for b in bridges:
            all_bridges.append(dict(b))

    if not all_bridges:
        return {"total": 0, "critical": 0, "items": []}

    # Build assessment lookup: station -> effect data
    assessment_lookup = {}
    if bridge_assessment:
        for detail in bridge_assessment.get("bridge_details", []):
            station = detail.get("station", "")
            assessment_lookup[station] = detail

    # Build bridge items
    for bridge in all_bridges:
        station = bridge.get("station", "")
        bridge_type = bridge.get("bridge_type", "未知")
        hw_code = bridge.get("highway_code", "")
        span = bridge.get("span", "")

        # Check assessment for effect ratio
        assess = assessment_lookup.get(station, {})
        max_ratio = assess.get("max_ratio", 0) if assess else 0
        passability = assess.get("passability", {}) if assess else {}

        # Determine priority
        priority, risk_desc = _bridge_priority(
            max_ratio, passability, station
        )

        if priority == PRIORITY_CRITICAL:
            critical += 1

        # Determine check items based on bridge type
        check_items = _bridge_check_items(bridge_type, max_ratio)

        # Build bridge name from type and span
        name = _bridge_display_name(bridge_type, span, station)

        items.append({
            "station": station,
            "name": name,
            "highway": hw_code,
            "type": bridge_type,
            "span": span,
            "effect_ratio": round(max_ratio, 3) if max_ratio else None,
            "check_items": check_items,
            "risk": risk_desc,
            "priority": priority,
        })

    # Sort by risk: CRITICAL first, then HIGH, then by position
    priority_rank = {PRIORITY_CRITICAL: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3}
    items.sort(key=lambda b: (
        priority_rank.get(b["priority"], 3),
        _parse_station_to_km(b["station"])
    ))

    return {
        "total": len(items),
        "critical": critical,
        "items": items,
    }


def _bridge_priority(max_ratio: float, passability: dict, station: str) -> tuple:
    """Determine bridge survey priority based on effect ratio."""
    grade = passability.get("grade", "")
    escort = passability.get("escort_required", False)
    reinforcement = passability.get("reinforcement_needed", False)
    max_speed = passability.get("max_speed_kmh")

    if reinforcement or max_ratio >= 1.0:
        priority = PRIORITY_CRITICAL
        if reinforcement:
            risk_desc = f"效应比值{max_ratio:.2f} - 需加固后方可通行"
        else:
            risk_desc = f"效应比值{max_ratio:.2f} - 需限速20km/h单车通行"
    elif max_ratio >= 0.9:
        priority = PRIORITY_CRITICAL
        risk_desc = f"效应比值{max_ratio:.2f} - 需限速20km/h单车通行"
    elif max_ratio >= 0.7:
        priority = PRIORITY_HIGH
        limit = f"≤{max_speed}km/h" if max_speed else "建议限速"
        risk_desc = f"效应比值{max_ratio:.2f} - 需{limit}"
    elif max_ratio >= 0.5:
        priority = PRIORITY_MEDIUM
        risk_desc = f"效应比值{max_ratio:.2f} - 注意控制车速"
    elif max_ratio > 0:
        priority = PRIORITY_LOW
        risk_desc = f"效应比值{max_ratio:.2f} - 正常通行"
    else:
        priority = PRIORITY_MEDIUM
        risk_desc = "无评估数据 - 需现场确认"

    return priority, risk_desc


def _bridge_check_items(bridge_type: str, max_ratio: float) -> list[str]:
    """Determine what to check for a given bridge type and risk level."""
    items = []

    if max_ratio >= 0.9:
        items.append("限重标志确认")
        items.append("桥面宽度测量")
        items.append("伸缩缝状态")

    # Type-specific checks
    type_lower = (bridge_type or "").lower()
    if "连续梁" in type_lower or "连续" in type_lower:
        items.append("支座状态检查")
        items.append("跨中挠度观测")
    elif "t梁" in type_lower or "t型" in type_lower:
        items.append("横隔板连接检查")
        items.append("湿接缝状态")
    elif "空心板" in type_lower:
        items.append("铰缝状态检查")
    elif "拱" in type_lower:
        items.append("拱圈裂缝检查")
        items.append("拱脚位移观测")
    elif "斜拉" in type_lower:
        items.append("斜拉索张力检查")

    # Common checks
    if "桥面铺装状态" not in items:
        items.append("桥面铺装状态")
    if "限高限宽标志" not in items:
        items.append("限高限宽标志确认")
    items.append("桥头跳车检查")

    return items[:6]  # Cap at 6 items


def _bridge_display_name(bridge_type: str, span: str, station: str) -> str:
    """Build a human-readable bridge name."""
    if bridge_type and span:
        return f"{bridge_type}({span})"
    elif bridge_type:
        return bridge_type
    return f"{station}桥梁"


def _build_tunnel_checklist(
    route_data: dict,
    highway_codes: list[str],
    vehicle_height: float,
) -> dict:
    """Build tunnel survey checklist.

    Checks vehicle height against standard 5.0m clearance.
    Flags if vehicle height > 4.5m.
    """
    tunnel_count = route_data.get("tunnel_count", 0)
    items = []
    critical = 0

    if tunnel_count <= 0:
        return {"total": 0, "critical": 0, "items": []}

    height_check = check_height(vehicle_height)
    height_status = height_check["status"]
    margin = height_check["margin"]

    for i in range(min(tunnel_count, 30)):
        tunnel_id = f"TUN-{i + 1:03d}"
        station = f"隧道#{i + 1}"

        if height_status == "fail":
            priority = PRIORITY_CRITICAL
            risk_desc = (
                f"车辆高度{vehicle_height}m超过标准净空{STANDARD_CLEARANCE_HEIGHT}m，"
                f"超出{abs(margin):.2f}m - 必须测量实际高度"
            )
            check_items = [
                "实际净空高度测量",
                "隧道入口限高标志",
                "隧道内通风管道高度",
                "隧道照明设备高度",
                "隧道消防管道高度",
            ]
            critical += 1
        elif height_status == "warning":
            priority = PRIORITY_HIGH
            risk_desc = (
                f"车辆高度{vehicle_height}m接近标准净空{STANDARD_CLEARANCE_HEIGHT}m，"
                f"仅余{margin:.2f}m - 需核实实际限高"
            )
            check_items = [
                "实际净空高度测量",
                "隧道入口限高标志",
                "隧道内最高点测量",
            ]
            if vehicle_height > 4.5:
                critical += 1
        else:
            priority = PRIORITY_LOW
            risk_desc = f"车辆高度{vehicle_height}m满足标准净空要求"
            check_items = [
                "隧道入口限高标志确认",
                "隧道宽度确认",
            ]

        items.append({
            "station": station,
            "tunnel_id": tunnel_id,
            "name": f"{station}",
            "highway": highway_codes[0] if highway_codes else "",
            "check_items": check_items,
            "risk": risk_desc,
            "priority": priority,
            "vehicle_height": vehicle_height,
            "standard_clearance": STANDARD_CLEARANCE_HEIGHT,
        })

    return {
        "total": len(items),
        "critical": critical,
        "items": items,
    }


def _build_toll_station_checklist(
    highway_codes: list[str],
    vehicle_width: float,
) -> dict:
    """Build toll station survey checklist.

    Checks vehicle width against 3.75m lane width.
    Flags if vehicle width > 3.0m.
    """
    items = []
    critical = 0

    # For each highway, estimate toll stations based on junctions
    # Typical toll stations are at highway endpoints/interchanges
    toll_stations = []
    for hw in highway_codes:
        # Find junctions on this highway (potential toll station locations)
        junctions = query(
            """SELECT junction_name, k_value, k_string FROM junction_positions
               WHERE highway_code = ? ORDER BY k_value""",
            (hw,)
        )
        for j in junctions:
            toll_stations.append({
                "name": j["junction_name"],
                "highway": hw,
                "station": j.get("k_string", f"K{j.get('k_value', 0):.0f}"),
            })

    if not toll_stations:
        return {"total": 0, "critical": 0, "items": []}

    width_check = check_width(vehicle_width)
    width_status = width_check["status"]
    margin = width_check["margin"]

    for ts in toll_stations:
        if width_status == "fail":
            priority = PRIORITY_CRITICAL
            risk_desc = (
                f"车辆宽度{vehicle_width}m超过标准车道{STANDARD_LANE_WIDTH}m，"
                f"超出{abs(margin):.2f}m - 必须确认超宽车道可用"
            )
            check_items = [
                "超宽车道宽度测量",
                "超宽车道限宽柱间距",
                "称重设备宽度",
                "收费岛间距",
            ]
            critical += 1
        elif width_status == "warning":
            priority = PRIORITY_HIGH
            risk_desc = (
                f"车辆宽度{vehicle_width}m接近车道宽度{STANDARD_LANE_WIDTH}m，"
                f"仅余{margin:.2f}m - 需确认超宽车道"
            )
            check_items = [
                "超宽车道宽度测量",
                "超宽车道限宽柱间距",
                "称重设备宽度",
            ]
            if vehicle_width > 3.0:
                critical += 1
        else:
            priority = PRIORITY_LOW
            risk_desc = f"车辆宽度{vehicle_width}m满足标准车道要求"
            check_items = [
                "超宽车道可用性确认",
                "ETC车道宽度",
            ]

        items.append({
            "station": ts["station"],
            "name": f"{ts['name']}收费站",
            "highway": ts["highway"],
            "check_items": check_items,
            "risk": risk_desc,
            "priority": priority,
            "vehicle_width": vehicle_width,
            "standard_lane_width": STANDARD_LANE_WIDTH,
        })

    return {
        "total": len(items),
        "critical": critical,
        "items": items,
    }


def _build_ramp_checklist(
    highway_codes: list[str],
    vehicle_length: float,
) -> dict:
    """Build interchange ramp survey checklist.

    Checks vehicle length against 15m minimum turning radius.
    Flags if vehicle_length > 20m.
    """
    items = []
    critical = 0

    turning_check = check_turning_radius(
        vehicle_length, DEFAULT_MIN_TURNING_RADIUS
    )
    turning_status = turning_check["status"]

    # Find interchange junctions (枢纽 type)
    for hw in highway_codes:
        junctions = query(
            """SELECT jp.junction_name, jp.k_value, jp.k_string,
                      j.junction_type
               FROM junction_positions jp
               JOIN junctions j ON jp.junction_name = j.junction_name
               WHERE jp.highway_code = ? AND j.junction_type = '枢纽'
               ORDER BY jp.k_value""",
            (hw,)
        )
        for j in junctions:
            jct_name = j["junction_name"]

            if turning_status == "fail":
                priority = PRIORITY_CRITICAL
                risk_desc = (
                    f"车辆长度{vehicle_length}m估计需要转弯半径"
                    f"{turning_check['estimated_required_radius']:.1f}m，"
                    f"超过匝道最小半径{DEFAULT_MIN_TURNING_RADIUS}m - 必须现场测量"
                )
                check_items = [
                    "匝道最小转弯半径测量",
                    "匝道宽度测量",
                    "匝道超高坡度",
                    "匝道视距检查",
                    "护栏位置确认",
                ]
                critical += 1
            elif turning_status == "warning":
                priority = PRIORITY_HIGH
                risk_desc = (
                    f"车辆长度{vehicle_length}m估计需要转弯半径"
                    f"{turning_check['estimated_required_radius']:.1f}m，"
                    f"匝道最小半径{DEFAULT_MIN_TURNING_RADIUS}m - 需谨慎评估"
                )
                check_items = [
                    "匝道最小转弯半径测量",
                    "匝道宽度测量",
                    "匝道超高坡度",
                ]
                if vehicle_length > 20:
                    critical += 1
            else:
                priority = PRIORITY_LOW
                risk_desc = f"车辆长度{vehicle_length}m满足匝道转弯要求"
                check_items = [
                    "匝道宽度确认",
                    "匝道转弯半径确认",
                ]

            items.append({
                "station": j.get("k_string", f"K{j.get('k_value', 0):.0f}"),
                "name": f"{jct_name}枢纽匝道",
                "highway": hw,
                "check_items": check_items,
                "risk": risk_desc,
                "priority": priority,
                "vehicle_length": vehicle_length,
                "min_turning_radius": DEFAULT_MIN_TURNING_RADIUS,
                "estimated_required_radius": turning_check.get(
                    "estimated_required_radius", 0
                ),
            })

    if not items:
        # If no 枢纽 type junctions, use all junctions as potential ramp locations
        for hw in highway_codes:
            junctions = query(
                """SELECT junction_name, k_value, k_string FROM junction_positions
                   WHERE highway_code = ? ORDER BY k_value""",
                (hw,)
            )
            # Sample up to 5 per highway
            for j in junctions[:5]:
                jct_name = j["junction_name"]
                check_items = [
                    "匝道宽度确认",
                    "匝道转弯半径确认",
                ]
                risk_desc = "车辆较长，需确认匝道通过性" if vehicle_length > 20 else "标准匝道宽度确认"
                items.append({
                    "station": j.get("k_string", f"K{j.get('k_value', 0):.0f}"),
                    "name": f"{jct_name}互通匝道",
                    "highway": hw,
                    "check_items": check_items,
                    "risk": risk_desc,
                    "priority": PRIORITY_MEDIUM,
                    "vehicle_length": vehicle_length,
                    "min_turning_radius": DEFAULT_MIN_TURNING_RADIUS,
                    "estimated_required_radius": turning_check.get(
                        "estimated_required_radius", 0
                    ),
                })

    return {
        "total": len(items),
        "critical": critical,
        "items": items,
    }


def _build_overhead_checklist(
    highway_codes: list[str],
    vehicle_height: float,
) -> dict:
    """Build overhead obstacle survey checklist.

    Identifies gantry signs, ETC frames, power lines, and other
    overhead obstructions that may impede tall vehicles.
    """
    items = []
    critical = 0

    height_check = check_height(vehicle_height)
    height_status = height_check["status"]
    margin = height_check["margin"]

    # For each highway, identify known overhead obstacle locations
    # These are estimated from junction positions and bridge data
    for hw in highway_codes:
        # Bridges along the highway can indicate potential overhead structures
        bridges = query(
            """SELECT station, bridge_type, span FROM bridges
               WHERE highway_code = ?
               ORDER BY station LIMIT 10""",
            (hw,)
        )

        for b in bridges:
            station = b["station"]
            # Each bridge location is a potential overhead obstacle point

            for obs_type in OVERHEAD_OBSTACLE_TYPES[:3]:  # Sample check types
                if height_status == "fail":
                    priority = PRIORITY_CRITICAL
                    risk_desc = (
                        f"车辆高度{vehicle_height}m超过{STANDARD_CLEARANCE_HEIGHT}m，"
                        f"必须确认{obs_type}实际高度"
                    )
                    check_items = [
                        f"{obs_type}实际高度测量",
                        "限高标志位置确认",
                    ]
                    if obs_type == "ETC门架":
                        critical += 1
                elif height_status == "warning":
                    priority = PRIORITY_HIGH
                    risk_desc = (
                        f"车辆高度{vehicle_height}m接近上限，"
                        f"仅余{margin:.2f}m，需核实{obs_type}高度"
                    )
                    check_items = [
                        f"{obs_type}实际高度测量",
                    ]
                else:
                    priority = PRIORITY_LOW
                    risk_desc = f"车辆高度{vehicle_height}m满足标准要求"
                    check_items = [
                        f"{obs_type}限高标志确认",
                    ]

                items.append({
                    "station": station,
                    "name": f"{obs_type}({station})",
                    "highway": hw,
                    "obstacle_type": obs_type,
                    "check_items": check_items,
                    "risk": risk_desc,
                    "priority": priority,
                    "vehicle_height": vehicle_height,
                    "standard_clearance": STANDARD_CLEARANCE_HEIGHT,
                })

        # Add 2 overhead points per highway if few bridges
        if len(bridges) < 2:
            for i in range(min(2, 5 - len(bridges))):
                station = f"K{100 + i * 50}"
                obs_type = OVERHEAD_OBSTACLE_TYPES[i % len(OVERHEAD_OBSTACLE_TYPES)]
                priority = PRIORITY_MEDIUM
                risk_desc = f"建议确认{obs_type}实际高度"
                items.append({
                    "station": station,
                    "name": f"{obs_type}({station})",
                    "highway": hw,
                    "obstacle_type": obs_type,
                    "check_items": [f"{obs_type}实际高度测量"],
                    "risk": risk_desc,
                    "priority": priority,
                    "vehicle_height": vehicle_height,
                    "standard_clearance": STANDARD_CLEARANCE_HEIGHT,
                })

    # Cap at 15 overhead items
    items = items[:15]

    return {
        "total": len(items),
        "critical": critical,
        "items": items,
    }


def _build_suggested_route(categories: dict) -> list[str]:
    """Build a suggested survey route ordered by station position.

    Returns list of checkpoint names in suggested visit order.
    """
    all_points = []

    # Collect all items with station info
    for cat_name, cat_data in categories.items():
        for item in cat_data.get("items", []):
            station = item.get("station", "")
            name = item.get("name", station)
            priority = item.get("priority", PRIORITY_LOW)

            # Parse K value for sorting
            k_val = _parse_station_to_km(station)

            all_points.append({
                "k_value": k_val,
                "label": f"{station} {name}",
                "priority": priority,
            })

    # Sort: CRITICAL first, then by K value (position along route)
    priority_rank = {PRIORITY_CRITICAL: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3}
    all_points.sort(key=lambda p: (
        priority_rank.get(p["priority"], 3),  # Lower rank = higher priority
        p["k_value"],
    ))

    return [p["label"] for p in all_points[:50]]  # Cap at 50


def _estimate_survey_time(
    total_points: int,
    bridge_items: dict,
    tunnel_items: dict,
) -> float:
    """Estimate survey time in hours.

    Rough estimates:
    - Bridge: 20 min each
    - Tunnel: 15 min each
    - Toll station: 10 min each
    - Ramp: 15 min each
    - Overhead: 5 min each
    """
    bridge_time = bridge_items.get("total", 0) * 20
    tunnel_time = tunnel_items.get("total", 0) * 15

    # Other categories estimated from remainder
    other_points = total_points - bridge_items.get("total", 0) - tunnel_items.get("total", 0)
    other_time = other_points * 10

    total_minutes = bridge_time + tunnel_time + other_time
    hours = total_minutes / 60.0

    # Minimum 1 hour, round to nearest 0.5
    hours = max(1.0, hours)
    return round(hours * 2) / 2.0  # Round to nearest 0.5


def _determine_equipment(
    vehicle_height: float,
    vehicle_width: float,
    total_weight: float,
    bridge_items: dict,
) -> list[str]:
    """Determine required survey equipment based on vehicle and route."""
    equipment = list(SURVEY_EQUIPMENT)

    # Add specialized equipment based on conditions
    if vehicle_height > 4.5:
        if "激光测高仪" not in equipment:
            equipment.append("激光测高仪")

    if vehicle_width > 3.0:
        equipment.append("轮距测量仪")

    if total_weight > 55.0:
        equipment.append("桥梁挠度测量仪")

    if bridge_items.get("total", 0) > 5:
        equipment.append("桥梁裂缝观测仪")

    equipment.append("无人机(可选)")

    return equipment


# Singleton
road_surveyor = RoadSurveyor()
