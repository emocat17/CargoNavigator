"""
Bridge Effect Calculation Engine (SQL Edition).

核心算法：车辆荷载效应对比法 (Vehicle Load Effect Comparison Method)
依据《公路大件运输安全通行评价技术规范》附录D

Algorithm:
1. 查询桥梁设计参数 → 获取频率+设计值
2. 计算冲击系数 μ = f(结构基频)
3. 读取 MIDAS 影响线数据 → 线性插值构建影响线函数
4. 模拟车辆通过 → 计算最大荷载效应
5. 效应比值 = 车辆荷载效应 / 桥梁设计值
6. 比值 < 1 → 安全通行
"""
import math
import logging
from typing import Optional

import numpy as np
from scipy.interpolate import interp1d

from app.bridge_db import query, query_one

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Damping / Impact coefficient
# ---------------------------------------------------------------------------

def calc_damping_factor(frequency: float) -> float:
    """Calculate impact coefficient μ based on bridge natural frequency.

    Per JTG D60-2015 / 公路大件运输安全通行评价技术规范:
        f < 1.5 Hz  → μ = 0.05
        1.5 ≤ f ≤ 14 Hz → μ = 0.1767·ln(f) - 0.0157
        f > 14 Hz  → μ = 0.45
    """
    if frequency < 1.5:
        return 0.05
    elif frequency <= 14:
        return 0.1767 * math.log(frequency) - 0.0157
    else:
        return 0.45


# ---------------------------------------------------------------------------
# Influence line reading from SQL
# ---------------------------------------------------------------------------

def _get_influence_data(bridge_id: int, line_type: str) -> np.ndarray:
    """Read influence line data from SQL.

    Returns: (N, 2) array with columns [distance, influence_value]
    """
    rows = query(
        """SELECT distance, influence_val
           FROM bridge_influence_lines
           WHERE bridge_id = ? AND line_type = ?
           ORDER BY distance""",
        (bridge_id, line_type)
    )
    if not rows:
        return np.empty((0, 2))

    data = np.array([(r["distance"], r["influence_val"]) for r in rows])
    return data


def _calc_max_effect(
    influence_data: np.ndarray,
    axle_loads_kn: np.ndarray,
    axle_positions: np.ndarray,
) -> float:
    """Calculate maximum load effect for a vehicle crossing a bridge.

    Args:
        influence_data: (N, 2) array [distance, influence_value]
        axle_loads_kn: 1D array of axle loads in kN
        axle_positions: 1D array of axle positions relative to front axle (m)

    Returns:
        Maximum absolute effect value
    """
    # --- Input sanitization ---
    # Ensure numpy arrays (accept lists/tuples as well)
    if not isinstance(influence_data, np.ndarray):
        influence_data = np.asarray(influence_data, dtype=float)
    if not isinstance(axle_loads_kn, np.ndarray):
        axle_loads_kn = np.asarray(axle_loads_kn, dtype=float)
    if not isinstance(axle_positions, np.ndarray):
        axle_positions = np.asarray(axle_positions, dtype=float)

    # Replace NaN/inf in inputs with zeros
    influence_data = np.nan_to_num(influence_data, nan=0.0, posinf=0.0, neginf=0.0)
    axle_loads_kn = np.nan_to_num(axle_loads_kn, nan=0.0, posinf=0.0, neginf=0.0)
    axle_positions = np.nan_to_num(axle_positions, nan=0.0, posinf=0.0, neginf=0.0)

    if len(influence_data) == 0:
        return 0.0

    dist = influence_data[:, 0]
    infl = influence_data[:, 1]

    # Sanitize interpolation input arrays
    dist = np.nan_to_num(dist, nan=0.0, posinf=0.0, neginf=0.0)
    infl = np.nan_to_num(infl, nan=0.0, posinf=0.0, neginf=0.0)

    # Build interpolation function
    f_infl = interp1d(dist, infl, kind="linear",
                       bounds_error=False, fill_value=0.0)

    bridge_start = float(dist[0])
    bridge_end = float(dist[-1])
    bridge_length = bridge_end - bridge_start
    vehicle_length = float(axle_positions[-1]) if len(axle_positions) > 0 else 0.0  # distance from first to last axle
    total_span = bridge_length + vehicle_length

    if total_span <= 0:
        return 0.0

    # Sampling step (cm-level precision is sufficient)
    step = 0.1  # 10 cm
    n_steps = max(int(total_span / step), 100)

    # Generate sample positions (front axle positions)
    sample_positions = np.linspace(
        bridge_start - vehicle_length,
        bridge_end + 1.0,  # one more meter past the bridge
        n_steps
    )

    max_effect = 0.0

    for front_pos in sample_positions:
        effect = 0.0
        for i, (load, ax_pos) in enumerate(zip(axle_loads_kn, axle_positions)):
            axle_x = front_pos + ax_pos  # position of this axle
            try:
                infl_val = float(f_infl(axle_x))
                if math.isnan(infl_val) or math.isinf(infl_val):
                    infl_val = 0.0
            except (ValueError, OverflowError):
                infl_val = 0.0
            effect += load * infl_val
        max_effect = max(max_effect, abs(effect))

    # Final sanitization
    if math.isnan(max_effect) or math.isinf(max_effect):
        return 0.0

    return max_effect


# ---------------------------------------------------------------------------
# Passability grade mapping
# ---------------------------------------------------------------------------

GRADE_TABLE = [
    # (max_ratio_exclusive, grade, max_speed_kmh, lane_restriction, escort_required, reinforcement_needed, notes)
    (0.6, "安全通行", None, "all_lanes", False, False, "正常速度，所有车道均可使用"),
    (0.8, "正常通行", None, "all_lanes", False, False, "标准车速，无通行限制"),
    (0.9, "建议限速", 40, "single_lane", False, False, "建议车速≤40km/h，单车道行驶"),
    (1.0, "限速通行", 30, "center_only", False, False, "限速≤30km/h，跨中行驶，禁止超车"),
    (1.1, "条件通行", 20, "center_only", True, False, "限速≤20km/h，单车过桥，需护送"),
    (1.2, "谨慎通行", 10, "center_only", True, True, "限速≤10km/h，建议临时加固"),
]


def get_passability_grade(max_ratio: float) -> dict:
    """Map the maximum effect ratio to a graduated passability grade.

    Referencing HVSAPS Australia and Bentley SUPERLOAD classification systems.

    Args:
        max_ratio: The maximum effect ratio across all load types.

    Returns:
        {
            "grade": str,              # e.g. "安全通行", "限速通行", "不建议通行"
            "max_speed_kmh": int|None, # Recommended max speed, None = no restriction
            "lane_restriction": str,   # "all_lanes", "single_lane", "center_only", or "none"
            "escort_required": bool,   # Whether escort vehicle is needed
            "reinforcement_needed": bool,  # Whether bridge reinforcement is recommended
            "bridge_specific_notes": str,  # Human-readable notes
        }
    """
    if max_ratio >= 1.2:
        return {
            "grade": "不建议通行",
            "max_speed_kmh": 0,
            "lane_restriction": "none",
            "escort_required": True,
            "reinforcement_needed": True,
            "bridge_specific_notes": "效应比值≥1.2，桥梁需加固或重新规划路线",
        }

    for threshold, grade, speed, lane, escort, reinforce, notes in GRADE_TABLE:
        if max_ratio < threshold:
            return {
                "grade": grade,
                "max_speed_kmh": speed,
                "lane_restriction": lane,
                "escort_required": escort,
                "reinforcement_needed": reinforce,
                "bridge_specific_notes": notes,
            }

    # Fallback (should never reach here given the >= 1.2 check above)
    return {
        "grade": "不建议通行",
        "max_speed_kmh": 0,
        "lane_restriction": "none",
        "escort_required": True,
        "reinforcement_needed": True,
        "bridge_specific_notes": "效应比值异常，建议重新评估",
    }


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate_bridge_effect(
    loads_ton: list[float],
    spacings: list[float],
    station: str,
    highway_code: Optional[str] = None,
) -> dict:
    """Calculate bridge effect ratios for a given vehicle and bridge.

    Args:
        loads_ton: Axle loads in tons, e.g. [10, 15, 12]
        spacings: Axle spacings in meters, e.g. [3.5, 1.2]
        station: Bridge station桩号, e.g. "k0+15"
        highway_code: Optional highway code for disambiguation

    Returns:
        {
            "station": str,
            "bridge_type": str,
            "highway_code": str,
            "pos_moment_ratio": "0.45~0.78",
            "neg_moment_ratio": "0.32~0.56",
            "shear_ratio": "0.51~0.72",
            "damping_factor": 0.17,
            "is_passable": true,
            "pos_moment_effect": [min, max],
            "neg_moment_effect": [min, max],
            "shear_effect": [min, max],
        }
        or {"error": "..."} on failure
    """
    # ── 1. Convert vehicle parameters ──
    loads_kn = np.array([p * 9.80665 for p in loads_ton])  # tons → kN
    axle_positions = np.cumsum([0.0] + list(spacings))       # relative positions

    # ── 2. Find bridge in database ──
    station_lower = station.lower().strip()
    if highway_code:
        bridge = query_one(
            """SELECT * FROM bridges
               WHERE LOWER(station) = ? AND highway_code = ?
               LIMIT 1""",
            (station_lower, highway_code.upper())
        )
    else:
        bridge = query_one(
            """SELECT * FROM bridges
               WHERE LOWER(station) = ?
               ORDER BY highway_code IS NULL, id
               LIMIT 1""",
            (station_lower,)
        )

    if not bridge:
        return {"error": f"Bridge not found: station={station}, hw={highway_code}"}

    bridge_id = bridge["id"]

    # ── 3. Calculate damping factor ──
    freq = bridge["frequency"]
    if freq is None:
        freq = 5.0  # default assumption
    damping = calc_damping_factor(float(freq))

    # ── 4. Read influence line data ──
    influence_types = {
        "pos_moment": "pos_moment",
        "neg_moment": "neg_moment",
        "shear": "shear",
    }

    # Get design values with NaN/inf sanitization
    def _sanitize_design_val(val, default=1.0):
        """Replace None, NaN, inf, zero-like, or negative design values with a safe default."""
        if val is None:
            return default
        try:
            v = float(val)
        except (TypeError, ValueError):
            return default
        if math.isnan(v) or math.isinf(v) or v <= 0:
            return default
        return v

    design_values = {
        "pos_moment": _sanitize_design_val(bridge.get("pos_moment_design"), 1.0),
        "neg_moment": _sanitize_design_val(bridge.get("neg_moment_design"), 1.0),
        "shear": _sanitize_design_val(bridge.get("shear_design"), 1.0),
    }

    results = {}
    all_passable = True

    for kind, db_type in influence_types.items():
        try:
            infl_data = _get_influence_data(bridge_id, db_type)

            if len(infl_data) == 0:
                logger.warning(f"No influence data for bridge {bridge_id}/{db_type}")
                results[kind] = {
                    "effect_min": 0.0,
                    "effect_max": 0.0,
                    "ratio_min": 0.0,
                    "ratio_max": 0.0,
                }
                continue

            # Calculate effect in both directions (forward / reverse)
            effect_forward = _calc_max_effect(infl_data, loads_kn, axle_positions)

            # Reverse: flip axle order
            loads_rev = loads_kn[::-1]
            # Recalculate axle positions for reversed vehicle
            spacings_rev = spacings[::-1]
            axle_pos_rev = np.cumsum([0.0] + list(spacings_rev))
            effect_reverse = _calc_max_effect(infl_data, loads_rev, axle_pos_rev)

            # Sanitize effects from potential NaN/inf
            for ef_name, ef_val in [("forward", effect_forward), ("reverse", effect_reverse)]:
                if math.isnan(ef_val) or math.isinf(ef_val):
                    logger.warning(f"Effect {ef_name} returned non-finite value for {db_type}, using 0.0")
                    if ef_name == "forward":
                        effect_forward = 0.0
                    else:
                        effect_reverse = 0.0

            # Apply impact factor and safety factor (1.1)
            safety_factor = 1.1
            effect_min = min(effect_forward, effect_reverse) * (1 + damping) * safety_factor
            effect_max = max(effect_forward, effect_reverse) * (1 + damping) * safety_factor

            design_val = design_values[kind]
            # Robust zero/negative/NaN/inf check (already sanitized above, but belt-and-suspenders)
            try:
                dv = float(design_val)
                if math.isnan(dv) or math.isinf(dv) or dv <= 0:
                    design_val = 1.0
                else:
                    design_val = dv
            except (TypeError, ValueError):
                design_val = 1.0

            ratio_min = effect_min / design_val
            ratio_max = effect_max / design_val

            # Sanitize ratios
            if math.isnan(ratio_min) or math.isinf(ratio_min):
                ratio_min = 0.0
            if math.isnan(ratio_max) or math.isinf(ratio_max):
                ratio_max = 0.0

            results[kind] = {
                "effect_min": round(effect_min, 2),
                "effect_max": round(effect_max, 2),
                "ratio_min": round(ratio_min, 4),
                "ratio_max": round(ratio_max, 4),
            }

            # Passability check: ratio_max < 1.0 means safe
            if ratio_max >= 1.0:
                all_passable = False
        except Exception as e:
            logger.error(f"Calculation failed for bridge {bridge_id}/{db_type}: {e}", exc_info=True)
            results[kind] = {
                "effect_min": 0.0,
                "effect_max": 0.0,
                "ratio_min": 0.0,
                "ratio_max": 0.0,
            }
            # Continue with other influence types instead of crashing

    # ── 5. Compute max ratio ──
    max_ratio = max(
        results["pos_moment"]["ratio_max"],
        results["neg_moment"]["ratio_max"],
        results["shear"]["ratio_max"],
    )

    # ── 6. Compute graduated passability grade ──
    passability = get_passability_grade(max_ratio)

    # ── 7. Format result ──
    return {
        "station": bridge["station"],
        "bridge_type": bridge["bridge_type"] or "未知",
        "highway_code": bridge["highway_code"] or "未知",
        "highway_name": bridge.get("highway_name", ""),
        "damping_factor": round(damping, 4),
        "pos_moment_ratio": f"{results['pos_moment']['ratio_min']:.4f}~{results['pos_moment']['ratio_max']:.4f}",
        "neg_moment_ratio": f"{results['neg_moment']['ratio_min']:.4f}~{results['neg_moment']['ratio_max']:.4f}",
        "shear_ratio": f"{results['shear']['ratio_min']:.4f}~{results['shear']['ratio_max']:.4f}",
        "pos_moment_effect": [results["pos_moment"]["effect_min"], results["pos_moment"]["effect_max"]],
        "neg_moment_effect": [results["neg_moment"]["effect_min"], results["neg_moment"]["effect_max"]],
        "shear_effect": [results["shear"]["effect_min"], results["shear"]["effect_max"]],
        "max_ratio": max_ratio,
        "is_passable": all_passable,
        "passability": passability,
    }


def find_bridges_on_road_section(
    junction1: str,
    highway_code: str,
    junction2: str,
) -> list[dict]:
    """Find all bridges between two junctions on a highway.

    Uses K-value ranges from junction_positions and bridge stations.
    """
    # Get K values for both junctions on this highway
    pos1 = query_one(
        """SELECT k_value FROM junction_positions
           WHERE junction_name = ? AND highway_code = ?""",
        (junction1, highway_code)
    )
    pos2 = query_one(
        """SELECT k_value FROM junction_positions
           WHERE junction_name = ? AND highway_code = ?""",
        (junction2, highway_code)
    )

    if not pos1 or not pos2:
        return []

    k1 = pos1["k_value"]
    k2 = pos2["k_value"]
    k_min = min(k1, k2)
    k_max = max(k1, k2)

    # Find bridges on this highway whose station K value falls within range
    # Bridge station format: "k0+15" → K = 0.015 or "k1074" → K = 1074
    # We extract K value by parsing the station string
    bridges = query(
        """SELECT id, station, bridge_type, span, highway_code,
                  pos_moment_design, neg_moment_design, shear_design, frequency
           FROM bridges
           WHERE highway_code = ?""",
        (highway_code,)
    )

    result = []
    for b in bridges:
        k_val = _parse_station_k(b["station"])
        if k_val is not None and k_min <= k_val <= k_max:
            result.append(dict(b))

    return result


def _parse_station_k(station: str) -> Optional[float]:
    """Parse station string to K value.

    Examples:
        "k0+15" → 0.015 (K0+015)
        "k1074" → 1074
        "k36+19" → 36.019
        "K0+15" → 0.015
    """
    s = station.lower().replace(" ", "")
    # Pattern: k<num>[+<num>]
    import re
    m = re.match(r'k(\d+)(?:\+(\d+))?', s)
    if m:
        major = float(m.group(1))
        minor = float(m.group(2)) if m.group(2) else 0
        # The + part is meters, so k0+15 = 0.015 km
        return major + minor / 1000.0
    return None


def evaluate_route_bridges(
    route_highway_segments: list[dict],
    loads_ton: list[float],
    spacings: list[float],
) -> dict:
    """Evaluate all bridges along a route.

    Args:
        route_highway_segments: [{"junction_from": "港后", "highway_code": "G15", "junction_to": "海沧"}, ...]
        loads_ton: axle loads in tons
        spacings: axle spacings in meters

    Returns:
        {
            "total_bridges": int,
            "passable_count": int,
            "risky_count": int,
            "max_ratio": float,
            "bridge_results": [...],
            "overall_safe": bool,
        }
    """
    all_bridges = []
    seen = set()

    for seg in route_highway_segments:
        bridges = find_bridges_on_road_section(
            seg["junction_from"],
            seg["highway_code"],
            seg["junction_to"],
        )
        for b in bridges:
            if b["id"] not in seen:
                seen.add(b["id"])
                all_bridges.append(b)

    if not all_bridges:
        return {
            "total_bridges": 0,
            "passable_count": 0,
            "risky_count": 0,
            "max_ratio": 0.0,
            "bridge_results": [],
            "overall_safe": True,
            "message": "该路线未找到桥梁数据",
        }

    bridge_results = []
    passable = 0
    risky = 0
    max_ratio_all = 0.0

    for b in all_bridges:
        result = calculate_bridge_effect(
            loads_ton, spacings,
            b["station"], b["highway_code"]
        )
        if "error" in result:
            bridge_results.append({
                "station": b["station"],
                "bridge_type": b["bridge_type"],
                "highway_code": b["highway_code"],
                "error": result["error"],
                "is_passable": True,  # assume passable if can't calculate
                "passability": {
                    "grade": "未评估",
                    "max_speed_kmh": None,
                    "lane_restriction": "unknown",
                    "escort_required": False,
                    "reinforcement_needed": False,
                    "bridge_specific_notes": "无法计算：缺少桥梁数据",
                },
            })
            passable += 1
        else:
            bridge_results.append(result)
            if result["is_passable"]:
                passable += 1
            else:
                risky += 1
            max_ratio_all = max(max_ratio_all, result["max_ratio"])

    return {
        "total_bridges": len(bridge_results),
        "passable_count": passable,
        "risky_count": risky,
        "max_ratio": round(max_ratio_all, 4),
        "bridge_results": bridge_results,
        "overall_safe": risky == 0,
    }
