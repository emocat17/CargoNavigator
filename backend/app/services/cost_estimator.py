"""
Cost Estimation Service for oversized cargo transport.

Estimates ALL costs for an oversized cargo transport journey:
- Toll fees (from Amap API, passed through route_data)
- Fuel cost (calculated from distance, terrain, load weight)
- Escort cost (from regulation KB escort requirements)
- Permit fee (from regulation KB permit class)
- Insurance (estimated from cargo value or flat rate)

Configurable via .env / app.core.config.settings:
    FUEL_PRICE_PER_L, ESCORT_VEHICLE_COST_PER_DAY,
    POLICE_ESCORT_COST, DEFAULT_INSURANCE_COST
"""
import logging
from typing import Optional

from app.core.config import settings
from app.services.regulation_kb import regulation_kb, STANDARD_LIMITS

logger = logging.getLogger(__name__)

# ── Fuel consumption base rates by terrain (L/100km) ──
FUEL_RATE_HIGHWAY = 30    # 高速
FUEL_RATE_MIXED = 35      # 混合
FUEL_RATE_MOUNTAIN = 45   # 山路

# ── Permit fee ranges by class ──
PERMIT_FEE = {
    "I": {"min": 0, "max": 0, "description": "I类（尺寸重量符合标准，免许可费）"},
    "II": {"min": 500, "max": 1000, "description": "II类（重量超限，尺寸合规）"},
    "III": {"min": 1000, "max": 3000, "description": "III类（尺寸/重量严重超限）"},
}

# ── Third-party liability flat ranges ──
TPL_INSURANCE_MIN = 1000
TPL_INSURANCE_MAX = 3000

# ── Default average daily travel distance (km) ──
AVG_DAILY_KM = 400


class CostEstimator:
    """Comprehensive cost estimator for oversized cargo transport."""

    @staticmethod
    def estimate(
        route_data: dict,
        vehicle_info: dict,
        cargo_info: Optional[dict] = None,
    ) -> dict:
        """Estimate all transport costs for a given route and vehicle.

        Args:
            route_data: Route information. Expected keys (from route_assessor input):
                - distance: int (meters)
                - toll_cost: float (RMB, from Amap API)
                - route_description: str
                - tunnel_count: int
                - risk_warnings: list[str] (optional)
            vehicle_info: Vehicle parameters. Expected keys:
                - length: float (m)
                - width: float (m)
                - height: float (m)
                - weight: float (tons)
                - axle_count: int (optional)
                - vehicle_type: str (optional, "truck"|"train")
            cargo_info: Optional cargo details:
                - cargo_value: float (RMB, for insurance calculation)
                - cargo_type: str (description)

        Returns:
            {
                "total": 15800.00,
                "breakdown": {
                    "toll": {"amount": 158.0, "source": "Amap API", "note": "290.8km 高速"},
                    "fuel": {"amount": 8700.0, "source": "calculated", "note": "..."},
                    "escort": {"amount": 2400.0, "source": "regulation", "note": "..."},
                    "permit": {"amount": 2000.0, "source": "regulation", "note": "..."},
                    "insurance": {"amount": 1500.0, "source": "estimated", "note": "..."}
                },
                "warnings": [...],
                "estimated_days": 1.5
            }
        """
        cargo_info = cargo_info or {}
        warnings: list[str] = []

        distance_m = route_data.get("distance", 0)
        distance_km = distance_m / 1000.0

        # ── 1. Toll fees ──
        toll_amount = float(route_data.get("toll_cost", 0) or 0)
        toll_note = _toll_note(route_data, distance_km)

        # ── 2. Fuel cost ──
        fuel_amount, fuel_note = _calculate_fuel(
            distance_km, vehicle_info, route_data
        )

        # ── 3. Escort cost ──
        escort_result = _calculate_escort(
            distance_km, vehicle_info
        )
        if escort_result["warnings"]:
            warnings.extend(escort_result["warnings"])

        # ── 4. Permit fee ──
        permit_amount, permit_note = _calculate_permit(vehicle_info)

        # ── 5. Insurance ──
        insurance_amount, insurance_note = _calculate_insurance(cargo_info)

        # ── 6. Compose result ──
        breakdown = {
            "toll": {
                "amount": round(toll_amount, 2),
                "source": "Amap API",
                "note": toll_note,
            },
            "fuel": {
                "amount": round(fuel_amount, 2),
                "source": "calculated",
                "note": fuel_note,
            },
            "escort": {
                "amount": round(escort_result["amount"], 2),
                "source": "regulation",
                "note": escort_result["note"],
            },
            "permit": {
                "amount": round(permit_amount, 2),
                "source": "regulation",
                "note": permit_note,
            },
            "insurance": {
                "amount": round(insurance_amount, 2),
                "source": "estimated",
                "note": insurance_note,
            },
        }

        total = round(sum(b["amount"] for b in breakdown.values()), 2)
        estimated_days = max(distance_km / AVG_DAILY_KM, 0.5)

        return {
            "total": total,
            "breakdown": breakdown,
            "warnings": warnings,
            "estimated_days": round(estimated_days, 1),
        }


# ── Internal cost calculators ──

def _toll_note(route_data: dict, distance_km: float) -> str:
    """Generate human-readable toll note."""
    toll_dist = route_data.get("toll_distance", 0)
    if toll_dist and toll_dist > 0:
        toll_km = toll_dist / 1000.0
        return f"{toll_km:.1f}km 收费路段"
    return f"{distance_km:.1f}km （高德地图API返回）"


def _calculate_fuel(
    distance_km: float,
    vehicle_info: dict,
    route_data: dict,
) -> tuple[float, str]:
    """Calculate fuel cost based on distance, terrain, and load weight.

    Formula: distance_km × fuel_rate_L_per_100km / 100 × fuel_price_per_L

    Returns (amount, note).
    """
    fuel_price = float(getattr(settings, "FUEL_PRICE_PER_L", 7.5))

    # Determine base fuel rate from terrain indicators
    base_rate = _determine_fuel_rate(route_data)

    # Load correction: base_rate × (1 + 0.3 × load_tons / max_load_tons)
    weight = float(vehicle_info.get("total_weight", 49) or 49)
    max_load = _get_max_load_tons(vehicle_info)
    load_correction = 1.0
    if max_load > 0 and weight > 0:
        load_correction = 1.0 + 0.3 * (weight / max_load)

    corrected_rate = base_rate * load_correction

    # Fuel consumption in liters
    fuel_liters = distance_km * corrected_rate / 100.0
    fuel_amount = fuel_liters * fuel_price

    # Build note
    terrain_label = _terrain_label(route_data)
    note_parts = [
        f"{distance_km:.1f}km × {corrected_rate:.0f}L/100km × ¥{fuel_price}/L"
    ]
    if abs(load_correction - 1.0) > 0.01:
        note_parts.append(f"(载重修正{load_correction:.2f}，车重{weight:.0f}t/{max_load:.0f}t)")
    if terrain_label:
        note_parts.append(f"路况:{terrain_label}")

    note = "，".join(note_parts)
    return fuel_amount, note


def _determine_fuel_rate(route_data: dict) -> float:
    """Determine base fuel consumption rate from route characteristics.

    Returns L/100km.
    """
    route_desc = route_data.get("route_description", "")
    risk_warnings = route_data.get("risk_warnings", [])
    tunnel_count = route_data.get("tunnel_count", 0)

    # Mountain indicators
    mountain_keywords = ["山路", "盘山", "山", "mountain", "Mountain"]
    is_mountain = any(kw in route_desc for kw in mountain_keywords)
    if not is_mountain and risk_warnings:
        is_mountain = any(
            "山" in w or "mountain" in w.lower()
            for w in risk_warnings
        )

    # Highway indicators
    highway_keywords = ["高速", "expressway", "Expressway"]
    is_highway = any(kw in route_desc for kw in highway_keywords)

    if is_mountain and tunnel_count > 10:
        return FUEL_RATE_MOUNTAIN
    elif is_mountain:
        return FUEL_RATE_MOUNTAIN
    elif is_highway and tunnel_count <= 5:
        return FUEL_RATE_HIGHWAY
    elif is_highway:
        # Highway with some tunnels/terrain: between highway and mixed
        return (FUEL_RATE_HIGHWAY + FUEL_RATE_MIXED) / 2
    else:
        return FUEL_RATE_MIXED


def _terrain_label(route_data: dict) -> str:
    """Return a Chinese terrain label for notes."""
    rate = _determine_fuel_rate(route_data)
    if rate >= FUEL_RATE_MOUNTAIN:
        return "山路"
    elif rate <= FUEL_RATE_HIGHWAY:
        return "高速"
    else:
        return "混合"


def _get_max_load_tons(vehicle_info: dict) -> float:
    """Get the standard max load (tons) for this vehicle's axle configuration.

    Uses the same standard limits as regulation_kb.
    """
    axle_count = int(vehicle_info.get("axle_count", 0) or 0)
    vtype = vehicle_info.get("vehicle_type", "train")

    if axle_count <= 0:
        # Default: 6-axle train = 49t
        return 49.0

    limits = STANDARD_LIMITS["weight_by_axle"]
    if axle_count >= 6:
        return float(limits.get((6, "train"), 49))
    if axle_count == 5:
        return float(limits.get((5, "train"), 43))
    if axle_count == 4:
        key = (4, "train") if vtype in ("train", "汽车列车", "半挂") else (4, "truck")
        return float(limits.get(key, 36))
    if axle_count == 3:
        key = (3, "train") if vtype in ("train", "汽车列车", "半挂") else (3, "truck")
        return float(limits.get(key, 27))
    if axle_count == 2:
        return float(limits.get((2, "truck"), 18))

    return 49.0


def _calculate_escort(
    distance_km: float,
    vehicle_info: dict,
) -> dict:
    """Calculate escort vehicle cost from regulation requirements.

    Returns {"amount": float, "note": str, "warnings": list[str]}.
    """
    escort_cost_per_day = float(getattr(settings, "ESCORT_VEHICLE_COST_PER_DAY", 800))
    police_cost = float(getattr(settings, "POLICE_ESCORT_COST", 2000))

    # Get escort requirements from regulation knowledge base
    try:
        escort_req = regulation_kb.get_escort_requirements(vehicle_info)
    except Exception as e:
        logger.warning(f"Failed to get escort requirements: {e}")
        return {
            "amount": 0.0,
            "note": "无法获取护送要求（法规库查询失败）",
            "warnings": ["护送费无法计算，请手动确认"],
        }

    if not escort_req.get("escort_required", False):
        return {
            "amount": 0.0,
            "note": "I类或II类运输无需强制护送",
            "warnings": [],
        }

    escort_count = escort_req.get("min_escort_vehicles", 0)
    police_required = escort_req.get("police_escort_required", False)
    details_list = escort_req.get("details", [])

    transport_days = max(distance_km / AVG_DAILY_KM, 0.5)

    escort_amount = escort_count * transport_days * escort_cost_per_day
    note_parts = []

    if escort_count > 0:
        note_parts.append(
            f"{escort_count}辆护送车 × {transport_days:.1f}天 × ¥{escort_cost_per_day:.0f}/天"
        )
    else:
        note_parts.append("护送车辆数未确定")

    if police_required:
        escort_amount += police_cost
        note_parts.append(f"警车护送 ¥{police_cost:.0f}/次")

    warnings = []
    if escort_count == 0:
        warnings.append("护送车辆数量未确定，护送费按最低配置估算，实际以当地报价为准")
    else:
        warnings.append("护送费按默认单价估算，实际以当地报价为准")

    note = "，".join(note_parts)
    if details_list:
        # Append a summary of the most important detail
        note += f"（依据：{details_list[0][:60]}）"

    return {
        "amount": escort_amount,
        "note": note,
        "warnings": warnings,
    }


def _calculate_permit(vehicle_info: dict) -> tuple[float, str]:
    """Calculate permit fee based on regulation class.

    Returns (amount, note).
    """
    try:
        permit_class = regulation_kb.classify_permit(vehicle_info)
    except Exception as e:
        logger.warning(f"Failed to classify permit: {e}")
        return 0.0, "无法确定许可类别（法规库查询失败）"

    try:
        compliance = regulation_kb.check_dimension_compliance(vehicle_info)
    except Exception:
        compliance = {"violations": []}

    fee_info = PERMIT_FEE.get(permit_class, PERMIT_FEE["I"])
    permit_amount = fee_info["max"]  # Use max as conservative estimate

    # Build note
    violations = compliance.get("violations", [])
    class_name = {"I": "一类", "II": "二类", "III": "三类"}.get(permit_class, permit_class)

    if not violations:
        note = f"{class_name}许可（尺寸重量符合标准，免许可费）"
    else:
        violation_desc = "、".join(
            f"{v['dimension']}超标{v['excess']}{v['unit']}"
            for v in violations
        )
        note = f"{class_name}许可 ¥{fee_info['min']:.0f}-{fee_info['max']:.0f}（{violation_desc}）"

    return permit_amount, note


def _calculate_insurance(cargo_info: dict) -> tuple[float, str]:
    """Calculate insurance cost.

    - Cargo insurance: 0.3% of cargo value (if known), or flat rate
    - Third-party liability: flat 1000-3000 RMB

    Returns (amount, note).
    """
    default_insurance = float(getattr(settings, "DEFAULT_INSURANCE_COST", 1500))
    cargo_value = cargo_info.get("cargo_value")

    note_parts = []
    total_insurance = 0.0

    if cargo_value and float(cargo_value) > 0:
        cv = float(cargo_value)
        cargo_premium = cv * 0.003
        cargo_premium = max(cargo_premium, 500)  # Minimum cargo insurance
        total_insurance += cargo_premium
        note_parts.append(
            f"货物险 ¥{cargo_premium:.0f}（货值¥{cv:,.0f} × 0.3%）"
        )
    else:
        total_insurance += default_insurance * 0.5  # half for cargo
        note_parts.append(f"货物险 ¥{default_insurance * 0.5:.0f}（按默认估值估算）")

    # Third-party liability: flat
    tpl_amount = (TPL_INSURANCE_MIN + TPL_INSURANCE_MAX) / 2
    total_insurance += tpl_amount
    note_parts.append(
        f"第三者责任险 ¥{tpl_amount:.0f}（¥{TPL_INSURANCE_MIN}-{TPL_INSURANCE_MAX}）"
    )

    return total_insurance, " + ".join(note_parts)


# Singleton
cost_estimator = CostEstimator()
