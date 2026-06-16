"""
Vehicle Classification Service.

Per 《公路大件运输安全通行评价技术规范》:
- Size-based classification (A-E) by width, length, height
- Axle-load based classification (A-E) by max axle load
- Combined classification returns both

Grade ranking: A=0 (smallest) through E=4 (largest).
The overall grade is the worst (maximum) across all dimensions.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Grade ordering (for comparison) ──
GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
RANK_GRADE = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E"}


def _classify_width(width_m: float) -> str:
    """Classify vehicle width per regulation.

    A: (2.55, 3.0]
    B: (3.0, 3.5]
    C: (3.5, 3.75]
    D: (3.75, 4.5]
    E: >4.5
    """
    if width_m <= 2.55:
        return "A"
    elif width_m <= 3.0:
        return "A"
    elif width_m <= 3.5:
        return "B"
    elif width_m <= 3.75:
        return "C"
    elif width_m <= 4.5:
        return "D"
    else:
        return "E"


def _classify_length(length_m: float, trailer_type: str = "lowbed") -> str:
    """Classify vehicle length per regulation.

    Tractor + lowbed:
        A: <=17
        B: (17, 22]
        C: (22, 30]
        D: (30, 35]
        E: >35

    Tractor + hydraulic:
        A: <=22
        B: (22, 31]
        C: (31, 41]
        D: (41, 45]
        E: >45
    """
    if trailer_type == "hydraulic":
        if length_m <= 22:
            return "A"
        elif length_m <= 31:
            return "B"
        elif length_m <= 41:
            return "C"
        elif length_m <= 45:
            return "D"
        else:
            return "E"
    else:
        # Default: tractor + lowbed
        if length_m <= 17:
            return "A"
        elif length_m <= 22:
            return "B"
        elif length_m <= 30:
            return "C"
        elif length_m <= 35:
            return "D"
        else:
            return "E"


def _classify_height(height_m: float) -> str:
    """Classify vehicle height per regulation.

    A/B/C: (4.0, 4.5]
    D:     (4.5, 5.0]
    E:     >5.0
    """
    if height_m <= 4.0:
        return "A"
    elif height_m <= 4.5:
        return "A"  # Baseline A; width/length may elevate to B/C
    elif height_m <= 5.0:
        return "D"
    else:
        return "E"


def classify_size(
    length: float,
    width: float,
    height: float,
    trailer_type: str = "lowbed",
) -> dict:
    """Classify vehicle by size dimensions.

    Args:
        length: Vehicle length in meters (tractor + trailer)
        width: Vehicle width in meters
        height: Vehicle height in meters
        trailer_type: "lowbed" (default) or "hydraulic"

    Returns:
        {
            "grade": "A"|"B"|"C"|"D"|"E",
            "width_grade": "A"|"B"|"C"|"D"|"E",
            "length_grade": "A"|"B"|"C"|"D"|"E",
            "height_grade": "A"|"B"|"C"|"D"|"E",
            "details": {
                "width": {"value": float, "range": str, "grade": str},
                "length": {"value": float, "range": str, "grade": str, "trailer_type": str},
                "height": {"value": float, "range": str, "grade": str},
            }
        }
    """
    width_grade = _classify_width(width)
    length_grade = _classify_length(length, trailer_type)
    height_grade = _classify_height(height)

    # Overall grade = worst (max) of the three
    overall_rank = max(
        GRADE_RANK[width_grade],
        GRADE_RANK[length_grade],
        GRADE_RANK[height_grade],
    )
    overall_grade = RANK_GRADE[overall_rank]

    # Build human-readable range descriptions
    width_ranges = {
        "A": "≤3.0m",
        "B": "(3.0, 3.5]m",
        "C": "(3.5, 3.75]m",
        "D": "(3.75, 4.5]m",
        "E": ">4.5m",
    }
    if trailer_type == "hydraulic":
        length_ranges = {
            "A": "≤22m",
            "B": "(22, 31]m",
            "C": "(31, 41]m",
            "D": "(41, 45]m",
            "E": ">45m",
        }
    else:
        length_ranges = {
            "A": "≤17m",
            "B": "(17, 22]m",
            "C": "(22, 30]m",
            "D": "(30, 35]m",
            "E": ">35m",
        }
    height_ranges = {
        "A": "≤4.5m",
        "B": "≤4.5m",
        "C": "≤4.5m",
        "D": "(4.5, 5.0]m",
        "E": ">5.0m",
    }

    return {
        "grade": overall_grade,
        "width_grade": width_grade,
        "length_grade": length_grade,
        "height_grade": height_grade,
        "trailer_type": trailer_type,
        "details": {
            "width": {"value": width, "range": width_ranges[width_grade], "grade": width_grade},
            "length": {"value": length, "range": length_ranges[length_grade], "grade": length_grade, "trailer_type": trailer_type},
            "height": {"value": height, "range": height_ranges[height_grade], "grade": height_grade},
        },
    }


def classify_axle_load(max_axle_tons: float) -> dict:
    """Classify vehicle by maximum axle load.

    Per regulation:
        A: <=8 tons
        B: (8, 10] tons
        C: (10, 14] tons
        D: (14, 18] tons
        E: (18, 20] tons

    Args:
        max_axle_tons: Maximum single axle load in tons

    Returns:
        {
            "grade": "A"|"B"|"C"|"D"|"E",
            "max_axle_tons": float,
            "range": str,
        }
    """
    if max_axle_tons <= 8:
        grade = "A"
        range_desc = "≤8t"
    elif max_axle_tons <= 10:
        grade = "B"
        range_desc = "(8, 10]t"
    elif max_axle_tons <= 14:
        grade = "C"
        range_desc = "(10, 14]t"
    elif max_axle_tons <= 18:
        grade = "D"
        range_desc = "(14, 18]t"
    elif max_axle_tons <= 20:
        grade = "E"
        range_desc = "(18, 20]t"
    else:
        grade = "E"
        range_desc = ">20t (超出分级范围)"

    return {
        "grade": grade,
        "max_axle_tons": max_axle_tons,
        "range": range_desc,
    }


def classify_combined(vehicle_info: dict) -> dict:
    """Combined vehicle classification (size + axle load).

    Args:
        vehicle_info: {
            "length": float,     # meters
            "width": float,      # meters
            "height": float,     # meters
            "total_weight": float,  # tons
            "axis_weight": float,   # max axle weight in tons
            "axis_count": int,      # number of axles
            "trailer_type": Optional[str],  # "lowbed" or "hydraulic"
        }

    Returns:
        {
            "size_grade": "A"|"B"|"C"|"D"|"E",
            "axle_load_grade": "A"|"B"|"C"|"D"|"E",
            "combined_grade": "A"|"B"|"C"|"D"|"E",
            "size_classification": {...},
            "axle_load_classification": {...},
            "is_oversized": bool,
        }
    """
    length = float(vehicle_info.get("length", 17))
    width = float(vehicle_info.get("width", 2.55))
    height = float(vehicle_info.get("height", 4.0))
    max_axle = float(vehicle_info.get("axis_weight", 10))
    trailer_type = vehicle_info.get("trailer_type", "lowbed")
    total_weight = float(vehicle_info.get("total_weight", 49))

    size_result = classify_size(length, width, height, trailer_type)
    axle_result = classify_axle_load(max_axle)

    # Combined grade = worst of both
    overall_rank = max(
        GRADE_RANK[size_result["grade"]],
        GRADE_RANK[axle_result["grade"]],
    )
    combined_grade = RANK_GRADE[overall_rank]

    # A vehicle is oversized if any dimension exceeds standard limits
    # Standard highway limits (per regulation): width 2.55m, height 4.0m, length ~17m
    is_oversized = (
        width > 2.55
        or height > 4.0
        or (trailer_type == "hydraulic" and length > 22)
        or (trailer_type == "lowbed" and length > 17)
        or max_axle > 8
    )

    return {
        "size_grade": size_result["grade"],
        "axle_load_grade": axle_result["grade"],
        "combined_grade": combined_grade,
        "size_classification": size_result,
        "axle_load_classification": axle_result,
        "is_oversized": is_oversized,
    }
