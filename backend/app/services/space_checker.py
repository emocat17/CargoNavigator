"""
Space Passability Checking Service.

Per 《公路大件运输安全通行评价技术规范》:
Checks whether a vehicle can physically pass through expressway infrastructure
based on clearances, lane widths, turning radii, and bridge weight capacity.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Standard expressway design parameters (per Chinese highway design code)
STANDARD_CLEARANCE_HEIGHT = 5.0       # meters (standard expressway clearance)
STANDARD_LANE_WIDTH = 3.75            # meters (standard expressway lane width)
STANDARD_SHOULDER_WIDTH = 2.5         # meters (hard shoulder, for reference)
DEFAULT_MIN_TURNING_RADIUS = 15.0     # meters (minimum interchange ramp radius)
DEFAULT_BRIDGE_CAPACITY_TONS = 55.0   # tons (standard highway bridge design load)


def check_height(vehicle_height_m: float) -> dict:
    """Check vehicle height against standard expressway clearance.

    Standard expressway clearance: 5.0m

    Args:
        vehicle_height_m: Vehicle height in meters

    Returns:
        {
            "status": "pass"|"warning"|"fail",
            "vehicle_height": float,
            "clearance": float,
            "margin": float,         # positive = clearance remaining
            "message": str,
        }
    """
    clearance = STANDARD_CLEARANCE_HEIGHT
    margin = clearance - vehicle_height_m

    if margin < 0:
        return {
            "status": "fail",
            "vehicle_height": vehicle_height_m,
            "clearance": clearance,
            "margin": round(margin, 2),
            "message": (
                f"车辆高度 {vehicle_height_m}m 超过标准净空 {clearance}m，"
                f"超出 {abs(margin):.2f}m。必须确认沿线所有天桥、隧道、标志牌等设施的实际限高。"
            ),
        }
    elif margin < 0.5:
        return {
            "status": "warning",
            "vehicle_height": vehicle_height_m,
            "clearance": clearance,
            "margin": round(margin, 2),
            "message": (
                f"车辆高度 {vehicle_height_m}m 接近标准净空 {clearance}m，"
                f"仅余 {margin:.2f}m。建议核实沿途隧道/天桥限高，低速通过。"
            ),
        }
    else:
        return {
            "status": "pass",
            "vehicle_height": vehicle_height_m,
            "clearance": clearance,
            "margin": round(margin, 2),
            "message": f"车辆高度 {vehicle_height_m}m 满足标准净空 {clearance}m 要求。",
        }


def check_width(vehicle_width_m: float) -> dict:
    """Check vehicle width against standard lane width.

    Standard expressway lane width: 3.75m

    Args:
        vehicle_width_m: Vehicle width in meters

    Returns:
        {
            "status": "pass"|"warning"|"fail",
            "vehicle_width": float,
            "lane_width": float,
            "margin": float,         # positive = lane width exceeds vehicle width
            "message": str,
        }
    """
    lane_width = STANDARD_LANE_WIDTH
    margin = lane_width - vehicle_width_m

    if margin < 0:
        return {
            "status": "fail",
            "vehicle_width": vehicle_width_m,
            "lane_width": lane_width,
            "margin": round(margin, 2),
            "message": (
                f"车辆宽度 {vehicle_width_m}m 超过标准车道宽度 {lane_width}m，"
                f"超出 {abs(margin):.2f}m。需占用多车道行驶，须办理特殊通行许可并安排护送。"
            ),
        }
    elif margin < 0.75:
        return {
            "status": "warning",
            "vehicle_width": vehicle_width_m,
            "lane_width": lane_width,
            "margin": round(margin, 2),
            "message": (
                f"车辆宽度 {vehicle_width_m}m 接近车道宽度 {lane_width}m，"
                f"仅余 {margin:.2f}m。需确认收费站超宽车道可用性，建议安排前导车。"
            ),
        }
    else:
        return {
            "status": "pass",
            "vehicle_width": vehicle_width_m,
            "lane_width": lane_width,
            "margin": round(margin, 2),
            "message": f"车辆宽度 {vehicle_width_m}m 满足标准车道宽度要求。",
        }


def check_turning_radius(
    vehicle_length_m: float,
    min_radius_m: float = DEFAULT_MIN_TURNING_RADIUS,
) -> dict:
    """Check if a vehicle can navigate a turn of given minimum radius.

    Uses a simplified geometric model based on vehicle length.
    For a tractor-semitrailer, the required minimum turning radius is
    approximately 0.5 * vehicle length (conservative rule-of-thumb).

    Args:
        vehicle_length_m: Vehicle length in meters
        min_radius_m: Minimum curve radius to navigate (default 15m,
                      the minimum interchange ramp radius)

    Returns:
        {
            "status": "pass"|"warning"|"fail",
            "vehicle_length": float,
            "min_curve_radius": float,
            "estimated_required_radius": float,
            "message": str,
        }
    """
    # Conservative estimate: required radius ~ 0.5 * vehicle length
    # This aligns with typical semi-trailer turning geometry where
    # a 17m tractor-trailer needs about 8.5m minimum radius,
    # a 30m vehicle needs about 15m.
    estimated_required = vehicle_length_m * 0.5
    margin = min_radius_m - estimated_required

    if margin < 0:
        return {
            "status": "fail",
            "vehicle_length": vehicle_length_m,
            "min_curve_radius": min_radius_m,
            "estimated_required_radius": round(estimated_required, 2),
            "message": (
                f"车辆长度 {vehicle_length_m}m 估计需要最小转弯半径 "
                f"{estimated_required:.1f}m，超过路段最小曲线半径 "
                f"{min_radius_m}m。该车辆无法通过此弯道，需重新规划路线。"
            ),
        }
    elif margin < 5.0:
        return {
            "status": "warning",
            "vehicle_length": vehicle_length_m,
            "min_curve_radius": min_radius_m,
            "estimated_required_radius": round(estimated_required, 2),
            "message": (
                f"车辆长度 {vehicle_length_m}m 估计需要转弯半径 "
                f"{estimated_required:.1f}m，路段最小半径 {min_radius_m}m。"
                f"可通过但需低速谨慎驾驶，注意匝道和互通立交。"
            ),
        }
    else:
        return {
            "status": "pass",
            "vehicle_length": vehicle_length_m,
            "min_curve_radius": min_radius_m,
            "estimated_required_radius": round(estimated_required, 2),
            "message": (
                f"车辆长度 {vehicle_length_m}m 满足最小转弯半径 {min_radius_m}m 要求。"
            ),
        }


def check_weight(
    total_tons: float,
    max_bridge_capacity_tons: Optional[float] = None,
) -> dict:
    """Check vehicle total weight against bridge capacity.

    Args:
        total_tons: Vehicle gross weight in tons
        max_bridge_capacity_tons: Maximum bridge capacity in tons.
            If None, uses default expressway bridge capacity (55 tons).

    Returns:
        {
            "status": "pass"|"warning"|"fail",
            "total_weight": float,
            "bridge_capacity": float,
            "utilization_ratio": float,  # weight / capacity
            "message": str,
        }
    """
    capacity = max_bridge_capacity_tons if max_bridge_capacity_tons is not None else DEFAULT_BRIDGE_CAPACITY_TONS
    ratio = total_tons / capacity if capacity > 0 else float("inf")

    if ratio > 1.0:
        return {
            "status": "fail",
            "total_weight": total_tons,
            "bridge_capacity": capacity,
            "utilization_ratio": round(ratio, 3),
            "message": (
                f"车辆总重 {total_tons}t 超过桥梁承载能力 {capacity}t "
                f"(利用率 {ratio:.1%})。严禁通行，需进行桥梁加固或换用轻型车辆。"
            ),
        }
    elif ratio >= 0.8:
        return {
            "status": "warning",
            "total_weight": total_tons,
            "bridge_capacity": capacity,
            "utilization_ratio": round(ratio, 3),
            "message": (
                f"车辆总重 {total_tons}t 接近桥梁承载力 {capacity}t "
                f"(利用率 {ratio:.1%})。建议进行详细的桥梁荷载效应验算。"
            ),
        }
    else:
        return {
            "status": "pass",
            "total_weight": total_tons,
            "bridge_capacity": capacity,
            "utilization_ratio": round(ratio, 3),
            "message": (
                f"车辆总重 {total_tons}t 在桥梁承载力 {capacity}t 范围内。"
            ),
        }


def full_space_check(vehicle_info: dict) -> dict:
    """Comprehensive space passability check combining all dimensions.

    Args:
        vehicle_info: {
            "length": float,       # meters
            "width": float,        # meters
            "height": float,       # meters
            "total_weight": float, # tons
            "axis_weight": float,  # max axle weight
            "axis_count": int,     # number of axles
        }

    Returns:
        {
            "overall_pass": bool,
            "checks": {
                "height": {...},
                "width": {...},
                "turning_radius": {...},
                "weight": {...},
            },
            "failures": [...],
            "warnings": [...],
            "recommendations": [...],
        }
    """
    length = float(vehicle_info.get("length", 17))
    width = float(vehicle_info.get("width", 2.55))
    height = float(vehicle_info.get("height", 4.0))
    total_weight = float(vehicle_info.get("total_weight", 49))

    height_result = check_height(height)
    width_result = check_width(width)
    turning_result = check_turning_radius(length)
    weight_result = check_weight(total_weight)

    checks = {
        "height": height_result,
        "width": width_result,
        "turning_radius": turning_result,
        "weight": weight_result,
    }

    failures = []
    warnings = []
    recommendations = []

    for check_name, result in checks.items():
        label_map = {
            "height": "高度",
            "width": "宽度",
            "turning_radius": "转弯半径",
            "weight": "总重",
        }
        label = label_map.get(check_name, check_name)

        if result["status"] == "fail":
            failures.append(f"[{label}] {result['message']}")
        elif result["status"] == "warning":
            warnings.append(f"[{label}] {result['message']}")

    # Generate recommendations
    if height_result["status"] == "fail":
        recommendations.append(
            "高度超标：请核实沿线所有天桥、隧道、标志牌、架空线缆的实际高度，"
            "必要时协调相关部门临时拆除或提升设施。"
        )
    if width_result["status"] == "fail":
        recommendations.append(
            "宽度超标：需占用多车道通行，必须办理超限运输许可证，"
            "安排前导车和护送车，必要时临时封闭对向车道。"
        )
    if turning_result["status"] == "fail":
        recommendations.append(
            "转弯半径不足：该路线包含车辆无法通过的急弯，建议重新规划路线，"
            "避开小半径弯道和复杂互通立交。"
        )
    if weight_result["status"] == "fail":
        recommendations.append(
            "总重超标：严禁直接通行，需委托专业机构进行桥梁荷载验算，"
            "必要时进行桥梁临时加固或换用轻型运输方案。"
        )

    if not failures and warnings:
        recommendations.append(
            "部分指标接近限值，建议安排专业护送并低速通过，实时监测通行状态。"
        )
    elif not failures and not warnings:
        recommendations.append(
            "所有空间通过性检查均通过，车辆可在标准高速公路上正常通行。"
        )

    overall_pass = len(failures) == 0

    return {
        "overall_pass": overall_pass,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "recommendations": recommendations,
    }


# Singleton
space_checker = type("SpaceChecker", (), {
    "check_height": staticmethod(check_height),
    "check_width": staticmethod(check_width),
    "check_turning_radius": staticmethod(check_turning_radius),
    "check_weight": staticmethod(check_weight),
    "full_space_check": staticmethod(full_space_check),
})()
