"""
Regulation Knowledge Base - 大件运输法规知识库。

Provides structured queries against the regulations JSON knowledge base,
including permit classification, document requirements, escort planning,
dimension compliance checking, and penalty estimation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Path to the structured regulations data file
_REGULATIONS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "regulations.json"

# ── Standard over-limit thresholds (Article 3) ──
STANDARD_LIMITS = {
    "height_m": 4.0,
    "width_m": 2.55,
    "length_m": 18.1,
    "weight_by_axle": {
        (2, "truck"): 18.0,
        (3, "truck"): 25.0,
        (3, "train"): 27.0,
        (4, "truck"): 31.0,
        (4, "train"): 36.0,
        (5, "train"): 43.0,
        (6, "train"): 49.0,
    },
}

# ── Class thresholds (classification article) ──
CLASS_THRESHOLDS = {
    "I": {"height_m": 4.5, "width_m": 3.75, "length_m": 28, "weight_t": 100},
    "II": {"height_m": 4.5, "width_m": 3.75, "length_m": 28, "weight_gt_t": 100},
}

# ── Document checklists per permit class ──
BASE_DOCUMENTS = [
    "公路超限运输申请表（含货物名称、尺寸质量、起讫点、通行路线、行驶时间、车辆信息）",
    "承运人道路运输经营许可证",
    "经办人身份证件",
    "授权委托书",
    "车辆行驶证或临时行驶车号牌",
]

DOCUMENTS_BY_CLASS = {
    "I": BASE_DOCUMENTS,
    "II": BASE_DOCUMENTS + [
        "车货总体外廓尺寸轮廓图",
        "护送方案（含护送车辆配置方案、护送人员配备方案、护送路线说明、操作细则、异常处理预案）",
    ],
    "III": BASE_DOCUMENTS + [
        "车货总体外廓尺寸轮廓图",
        "护送方案（含护送车辆配置方案、护送人员配备方案、护送路线说明、操作细则、异常处理预案）",
        "载货时车货实际尺寸和重量的称重检测信息",
    ],
}


class RegulationKB:
    """大件运输法规知识库 —— 支持关键词搜索、许可分类、文件清单、护送方案、合规检查、处罚预估。"""

    def __init__(self, data_path: Optional[Path] = None):
        self._data_path = data_path or _REGULATIONS_PATH
        self._articles: list[dict] = []
        self._load()

    # ── internal helpers ──

    def _load(self) -> None:
        """Load the regulations JSON file into memory."""
        if not self._data_path.exists():
            logger.warning(f"Regulations file not found: {self._data_path}")
            return
        try:
            raw = self._data_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            self._articles = payload.get("articles", [])
            logger.info(f"Loaded {len(self._articles)} regulation articles from {self._data_path}")
        except Exception as exc:
            logger.error(f"Failed to load regulations: {exc}")
            self._articles = []

    @property
    def article_count(self) -> int:
        return len(self._articles)

    # ── public API ──

    def query(self, keywords: str | list[str]) -> list[dict]:
        """Search regulations by keywords (space-separated string or list).

        Returns articles scored by relevance (title/content/tag match).
        """
        if isinstance(keywords, str):
            kw_list = [kw.strip() for kw in keywords.split() if kw.strip()]
        else:
            kw_list = [str(k).strip() for k in keywords if str(k).strip()]

        if not kw_list:
            return []

        scored: list[tuple[int, dict]] = []
        for art in self._articles:
            score = 0
            title = art.get("title", "")
            content = art.get("content", "")
            tags = art.get("tags", [])
            for kw in kw_list:
                kw_lower = kw.lower()
                # Title match scores highest
                if kw_lower in title.lower():
                    score += 5
                # Tag match scores high
                if any(kw_lower in t.lower() for t in tags):
                    score += 3
                # Content match
                if kw_lower in content.lower():
                    score += 1
                # Article number match
                if art.get("article_number", "").lower() == kw_lower:
                    score += 10
            if score > 0:
                scored.append((score, art))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [art for _, art in scored]

    def classify_permit(self, vehicle_info: dict) -> str:
        """Classify a vehicle into permit class I / II / III.

        Args:
            vehicle_info: dict with optional keys:
                height (m), width (m), length (m), weight (tons),
                axle_count (int), vehicle_type ("truck"|"train")

        Returns:
            "I", "II", or "III"
        """
        height = float(vehicle_info.get("height", 0) or 0)
        width = float(vehicle_info.get("width", 0) or 0)
        length = float(vehicle_info.get("length", 0) or 0)
        weight = float(vehicle_info.get("total_weight", 0) or 0)

        # ---- first check: is it even over-limit ? ----
        is_over_limit = False
        if height > STANDARD_LIMITS["height_m"]:
            is_over_limit = True
        if width > STANDARD_LIMITS["width_m"]:
            is_over_limit = True
        if length > STANDARD_LIMITS["length_m"]:
            is_over_limit = True

        axle_count = int(vehicle_info.get("axle_count", 0) or 0)
        vtype = vehicle_info.get("vehicle_type", "train")
        if axle_count:
            weight_limit = self._get_weight_limit(axle_count, vtype)
            if weight_limit is not None and weight > weight_limit:
                is_over_limit = True

        if not is_over_limit:
            # Not over-limit by any measure — no permit required
            # But the API always returns a class; this means "within standard"
            return "I"

        # ---- class III check: any dimension exceeds Class I thresholds ----
        c1 = CLASS_THRESHOLDS["I"]
        if height > c1["height_m"]:
            return "III"
        if width > c1["width_m"]:
            return "III"
        if length > c1["length_m"]:
            return "III"

        # ---- class II check: weight exceeds 100t while dimensions within Class I ----
        if weight > CLASS_THRESHOLDS["II"]["weight_gt_t"]:
            return "II"

        # ---- class I: everything within Class I thresholds ----
        return "I"

    @staticmethod
    def _get_weight_limit(axle_count: int, vehicle_type: str) -> Optional[float]:
        """Return the standard weight limit (tons) for a given axle count and type."""
        limits = STANDARD_LIMITS["weight_by_axle"]
        vtype = vehicle_type.lower() if vehicle_type else "truck"

        if axle_count >= 6:
            return limits[(6, "train")]
        if axle_count == 5:
            return limits.get((5, "train"))
        if axle_count == 4:
            key = (4, "train") if vtype in ("train", "汽车列车", "半挂") else (4, "truck")
            return limits.get(key)
        if axle_count == 3:
            key = (3, "train") if vtype in ("train", "汽车列车", "半挂") else (3, "truck")
            return limits.get(key)
        if axle_count == 2:
            return limits.get((2, "truck"))

        return None

    def get_required_documents(self, permit_class: str) -> list[str]:
        """Return the document checklist for a given permit class (I/II/III)."""
        cls = permit_class.upper().strip()
        return DOCUMENTS_BY_CLASS.get(cls, DOCUMENTS_BY_CLASS["I"])

    def get_escort_requirements(self, vehicle_info: dict) -> dict:
        """Calculate escort vehicle requirements based on vehicle dimensions.

        Args:
            vehicle_info: dict with optional height, width, length (all in meters)

        Returns:
            {
                "escort_required": bool,
                "min_escort_vehicles": int,
                "police_escort_required": bool,
                "details": list[str]  — human-readable breakdown
            }
        """
        height = float(vehicle_info.get("height", 0) or 0)
        width = float(vehicle_info.get("width", 0) or 0)
        length = float(vehicle_info.get("length", 0) or 0)
        permit_class = vehicle_info.get("permit_class") or self.classify_permit(vehicle_info)

        result: dict[str, Any] = {
            "escort_required": False,
            "min_escort_vehicles": 0,
            "police_escort_required": False,
            "details": [],
        }

        # Escort is only mandatory for Class III
        if permit_class != "III":
            result["details"].append("I类或II类大件运输无需强制护送（但承运人可自行安排）")
            return result

        result["escort_required"] = True

        # Escort vehicle count based on the most severe dimension
        escort_config = self._get_escort_article()
        ew = escort_config.get("escort_vehicle_requirements", {})

        max_vehicles = 0

        # Width
        for band in ew.get("width", []):
            if band["min"] < width <= band["max"]:
                count = band["vehicles"]
                max_vehicles = max(max_vehicles, count)
                result["details"].append(
                    f"宽度{width:.2f}米（{band['min']}-{band['max']}米区间）: 需配备不少于{count}辆护送车辆"
                )
                break

        # Length
        for band in ew.get("length", []):
            if band["min"] < length <= band["max"]:
                count = band["vehicles"]
                max_vehicles = max(max_vehicles, count)
                result["details"].append(
                    f"长度{length:.2f}米（{band['min']}-{band['max']}米区间）: 需配备不少于{count}辆护送车辆"
                )
                break

        # Height
        for band in ew.get("height", []):
            if band["min"] < height <= band["max"]:
                count = band["vehicles"]
                max_vehicles = max(max_vehicles, count)
                result["details"].append(
                    f"高度{height:.2f}米（{band['min']}-{band['max']}米区间）: 需配备不少于{count}辆护送车辆"
                )
                break

        result["min_escort_vehicles"] = max_vehicles

        # Police escort check
        police_thresh = ew.get("police_escort_thresholds", {})
        if (
            width > police_thresh.get("width_m", 99)
            or length > police_thresh.get("length_m", 99)
            or height > police_thresh.get("height_m", 99)
        ):
            result["police_escort_required"] = True
            result["details"].append(
                "车辆尺寸超出警车护送阈值（宽度>4.5m 或 长度>35m 或 高度>5.0m），"
                "需由公路管理机构商请公安机关交通管理部门决定是否警车护送"
            )

        return result

    def _get_escort_article(self) -> dict:
        """Return the escort guide article dict."""
        for art in self._articles:
            if art.get("article_number") == "escort_guide":
                return art
        return {}

    def check_dimension_compliance(self, vehicle_info: dict) -> dict:
        """Check which dimensions exceed standard highway limits.

        Args:
            vehicle_info: dict with optional height, width, length, weight, axle_count

        Returns:
            {
                "is_compliant": bool,
                "violations": [
                    {"dimension": str, "limit": float, "actual": float, "excess": float, "unit": str}
                ],
                "permit_class": str,
                "summary": str,
            }
        """
        height = float(vehicle_info.get("height", 0) or 0)
        width = float(vehicle_info.get("width", 0) or 0)
        length = float(vehicle_info.get("length", 0) or 0)
        weight = float(vehicle_info.get("total_weight", 0) or 0)
        axle_count = int(vehicle_info.get("axle_count", 0) or 0)
        vtype = vehicle_info.get("vehicle_type", "truck")

        violations: list[dict] = []

        if height > STANDARD_LIMITS["height_m"]:
            violations.append({
                "dimension": "高度",
                "limit": STANDARD_LIMITS["height_m"],
                "actual": height,
                "excess": round(height - STANDARD_LIMITS["height_m"], 2),
                "unit": "米",
            })

        if width > STANDARD_LIMITS["width_m"]:
            violations.append({
                "dimension": "宽度",
                "limit": STANDARD_LIMITS["width_m"],
                "actual": width,
                "excess": round(width - STANDARD_LIMITS["width_m"], 2),
                "unit": "米",
            })

        if length > STANDARD_LIMITS["length_m"]:
            violations.append({
                "dimension": "长度",
                "limit": STANDARD_LIMITS["length_m"],
                "actual": length,
                "excess": round(length - STANDARD_LIMITS["length_m"], 2),
                "unit": "米",
            })

        if axle_count:
            weight_limit = self._get_weight_limit(axle_count, vtype)
            if weight_limit is not None and weight > weight_limit:
                violations.append({
                    "dimension": "总质量",
                    "limit": weight_limit,
                    "actual": weight,
                    "excess": round(weight - weight_limit, 2),
                    "unit": "吨",
                    "axle_count": axle_count,
                    "vehicle_type": vtype,
                })

        is_compliant = len(violations) == 0
        permit_class = self.classify_permit(vehicle_info)

        if is_compliant:
            summary = "车辆尺寸及重量符合公路标准，无需办理超限运输许可证。"
        else:
            parts = []
            for v in violations:
                parts.append(f"{v['dimension']}超标{v['excess']}{v['unit']}（标准{v['limit']}{v['unit']}，实际{v['actual']}{v['unit']}）")
            summary = f"车辆存在{len(violations)}项超限违规：{'；'.join(parts)}。需办理{self._class_name(permit_class)}大件运输许可证。"

        return {
            "is_compliant": is_compliant,
            "violations": violations,
            "permit_class": permit_class,
            "summary": summary,
        }

    def get_penalty_estimate(self, violations: Optional[list[dict]] = None,
                             vehicle_info: Optional[dict] = None) -> dict:
        """Estimate penalties for given violations or vehicle info.

        Must provide either violations (from check_dimension_compliance) or vehicle_info.

        Returns:
            {
                "size_penalty": {"min": float, "max": float, "description": str},
                "weight_penalty": {"amount": float, "description": str},
                "total_penalty": {"min": float, "max": float},
            }
        """
        if violations is None and vehicle_info is not None:
            compliance = self.check_dimension_compliance(vehicle_info)
            violations = compliance.get("violations", [])
        elif violations is None:
            violations = []

        size_penalty_min = 0.0
        size_penalty_max = 0.0
        weight_penalty = 0.0
        size_count = 0
        weight_excess = 0.0

        for v in violations:
            if v["dimension"] in ("高度", "宽度", "长度"):
                size_count += 1
                if v.get("excess", 0) > 0:
                    # 200-3000 per dimension violation
                    if v["excess"] > 2.0:  # severe
                        size_penalty_min += 1000
                        size_penalty_max += 3000
                    else:
                        size_penalty_min += 200
                        size_penalty_max += 1000
            elif v["dimension"] == "总质量":
                weight_excess = v.get("excess", 0)

        # Weight penalty: 500 per 1000kg over limit, max 30000
        if weight_excess > 0:
            excess_kg = weight_excess * 1000  # convert tons to kg
            if excess_kg <= 1000:
                weight_penalty = 0  # warning only
            else:
                weight_penalty = min((excess_kg / 1000) * 500, 30000.0)

        total_min = size_penalty_min + weight_penalty
        total_max = min(size_penalty_max + weight_penalty, 30000.0)

        penalty_article = ""
        for art in self._articles:
            if art.get("article_number") == "43":
                penalty_article = f"依据《超限运输车辆行驶公路管理规定》第43条"
                break

        description = []
        if size_count > 0:
            description.append(
                f"尺寸超限{size_count}项：每项罚款{size_penalty_min:.0f}-{size_penalty_max:.0f}元"
            )
        if weight_excess > 0:
            if weight_excess <= 1.0:
                description.append(f"重量超限{weight_excess:.2f}吨（未超过1000kg）：警告")
            else:
                description.append(f"重量超限{weight_excess:.2f}吨：罚款{weight_penalty:.0f}元（每超1000kg罚款500元）")

        return {
            "penalty_article": penalty_article,
            "size_penalty": {
                "min": size_penalty_min,
                "max": size_penalty_max,
                "description": f"尺寸超限罚款{size_penalty_min:.0f}-{size_penalty_max:.0f}元",
            },
            "weight_penalty": {
                "amount": weight_penalty,
                "description": f"重量超限罚款{weight_penalty:.0f}元" if weight_penalty > 0 else "重量未超限或超限≤1000kg仅警告",
            },
            "total_penalty": {
                "min": total_min,
                "max": total_max,
            },
            "details": description,
        }

    @staticmethod
    def _class_name(cls: str) -> str:
        mapping = {"I": "一类", "II": "二类", "III": "三类"}
        return mapping.get(cls, cls)

    def format_for_llm(self, vehicle_info: dict) -> str:
        """Produce a comprehensive regulation summary text for the LLM context."""
        permit_class = self.classify_permit(vehicle_info)
        compliance = self.check_dimension_compliance(vehicle_info)
        escort = self.get_escort_requirements(vehicle_info)
        documents = self.get_required_documents(permit_class)
        penalty = self.get_penalty_estimate(vehicle_info=vehicle_info)

        # Time limit and validity
        time_desc = "即时办理" if permit_class == "I" else (
            "2个工作日" if permit_class == "II" else "5个工作日"
        )
        validity_desc = "6个月" if permit_class == "I" else (
            "3个月" if permit_class == "II" else "1个月或按单次运输确定"
        )

        lines = [
            "【法规知识库查询结果】",
            "",
            f"许可类别：{self._class_name(permit_class)}大件运输",
            f"办理时限：{time_desc}",
            f"许可证有效期：{validity_desc}",
            f"审批机关：省级公路管理机构",
            "",
        ]

        if compliance["violations"]:
            lines.append("超限情况：")
            for v in compliance["violations"]:
                lines.append(f"  - {v['dimension']}：超标{v['excess']}{v['unit']}（限值{v['limit']}{v['unit']}）")
            lines.append("")

        lines.append("所需申请材料：")
        for i, doc in enumerate(documents, 1):
            lines.append(f"  {i}. {doc}")
        lines.append("")

        if escort["escort_required"]:
            lines.append(f"护送要求：需要护送（{'；'.join(escort['details'])}）")
            if escort["police_escort_required"]:
                lines.append("  [!] 需商请公安机关交通管理部门派警车护送")
        else:
            lines.append("护送要求：无需强制护送")

        lines.append("")
        if penalty["details"]:
            lines.append("处罚预估：")
            for d in penalty["details"]:
                lines.append(f"  - {d}")

        return "\n".join(lines)


# Singleton
regulation_kb = RegulationKB()
