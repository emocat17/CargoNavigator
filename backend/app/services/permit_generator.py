"""
Permit Application Generator Service.

Automatically generates complete oversized cargo transport permit applications
combining route assessments, vehicle/cargo information, safety recommendations,
and escort plans into structured application documents.

Reference: 特殊车辆路线调度垂直模型/大件运输垂直大模型-需计算的内容.docx
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# Escort vehicle requirements based on vehicle dimensions (reference regulation)
# Category 3 escort is mandatory for vehicles exceeding dimension thresholds
ESCORT_THRESHOLDS = {
    "length": 28.0,   # meters: escort required if total length >= 28m
    "width": 3.75,    # meters: escort required if width >= 3.75m
    "height": 4.5,    # meters: escort required if height >= 4.5m
    "weight": 100.0,  # tons: escort required if total weight >= 100 tons
}


class PermitGenerator:
    """Generate complete oversized cargo transport permit applications.

    Produces structured applications with all fields required by regulation
    Article 6, including applicant info, vehicle/cargo info, transport plan,
    route analysis, safety notes, and escort plans.
    """

    # ── Public API ──

    @staticmethod
    def generate_application(
        route_data: dict,
        vehicle_info: dict,
        cargo_info: dict,
        applicant_info: Optional[dict] = None,
        schedule_info: Optional[dict] = None,
    ) -> dict:
        """Generate a complete permit application.

        Args:
            route_data: Route information with keys:
                - routes: list of route dicts, each with:
                    - route_description: str, "起点--G76--终点"
                    - major_roads: list[str]
                    - distance: int (meters)
                    - duration: int (seconds)
                    - tunnel_count: int
                    - pros: list[str] (optional)
                    - cons: list[str] (optional)
                - assessment: dict (optional, from route_assessor)
            vehicle_info: Vehicle parameters:
                - vehicle_type: str (e.g. "牵引车+低平板半挂车")
                - length: float (m)
                - width: float (m)
                - height: float (m)
                - weight: float (tons)
                - axle_count: int
                - axle_spacings: list[float] (optional)
                - axle_loads: list[float] (optional)
                - tractor_length: float (optional)
                - trailer_length: float (optional)
                - tractor_axle_count: int (optional)
                - trailer_axle_count: int (optional)
                - first_axle_distance: float (optional)
            cargo_info: Cargo information:
                - name: str
                - length: float (m)
                - width: float (m)
                - height: float (m)
                - weight: float (tons)
            applicant_info: Applicant details (optional):
                - name: str
                - address: str
                - contact_person: str
                - phone: str
                - id_number: str
            schedule_info: Schedule details (optional):
                - departure_time: str or datetime
                - estimated_arrival: str or datetime

        Returns:
            Complete application dict with all permit fields.
        """
        app_id = str(uuid.uuid4())
        now = datetime.now()

        routes = route_data.get("routes", [])
        assessment = route_data.get("assessment", {})

        # Determine risk level from assessment or compute from vehicle info
        risk_level = PermitGenerator._determine_risk_level(
            vehicle_info, assessment
        )

        # Build each section
        application = {
            "application_id": app_id,
            "generated_at": now.isoformat(),
            "status": "DRAFT",

            # 1. Applicant info (Article 6)
            "applicant": PermitGenerator._build_applicant_section(
                applicant_info or {}
            ),

            # 2. Vehicle + cargo combined info (Article 6)
            "vehicle_cargo": PermitGenerator._build_vehicle_cargo_section(
                vehicle_info, cargo_info
            ),

            # 3. Cargo info (Article 6)
            "cargo": PermitGenerator._build_cargo_section(cargo_info),

            # 4. Transport plan (Article 6)
            "transport": PermitGenerator._build_transport_section(
                route_data, vehicle_info, schedule_info
            ),

            # 5. Route analysis
            "route_analysis": {
                "primary_route": PermitGenerator._format_route_entry(
                    routes[0], idx=0, is_primary=True
                ) if len(routes) > 0 else None,
                "alternative_routes": [
                    PermitGenerator._format_route_entry(r, idx=i, is_primary=False)
                    for i, r in enumerate(routes[1:], start=1)
                ],
                "route_description": PermitGenerator.generate_route_description(
                    routes
                ),
            },

            # 6. Safety notes
            "safety_notes": PermitGenerator.generate_safety_notes(assessment),

            # 7. Escort plan (mandatory for category 3)
            "escort_plan": PermitGenerator.generate_escort_plan(
                vehicle_info, risk_level
            ),

            # 8. Compliance summary
            "compliance": PermitGenerator._build_compliance_summary(
                vehicle_info, assessment, risk_level
            ),
        }

        return application

    @staticmethod
    def generate_route_description(routes: list[dict]) -> str:
        """Generate a formatted multi-route description text.

        Args:
            routes: List of route dicts with at minimum 'route_description'.

        Returns:
            Formatted string with route analysis suitable for approver review.
        """
        if not routes:
            return "（无可用路线）"

        lines = ["推荐路线及分析："]

        primary_labels = ["A", "B", "C", "D", "E"]

        for i, route in enumerate(routes):
            label = primary_labels[i] if i < len(primary_labels) else str(i + 1)
            desc = route.get("route_description", "未知路线")
            distance_km = round(route.get("distance", 0) / 1000, 1)
            duration_min = route.get("duration", 0) // 60

            if i == 0:
                title = f"1. 路线{label}（主推荐路线）"
            else:
                title = f"{i + 1}. 路线{label}（备用路线）"

            lines.append(f"   {title}")
            lines.append(f"   路径：{desc}")
            lines.append(f"   里程：{distance_km}公里，预计耗时：{duration_min}分钟")

            pros = route.get("pros", [])
            cons = route.get("cons", [])

            if pros:
                lines.append(f"   优点：{'；'.join(pros)}")
            if cons:
                lines.append(f"   缺点：{'；'.join(cons)}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_safety_notes(assessment: dict) -> list[str]:
        """Generate safety recommendations from an assessment.

        Extracts safety-relevant findings from the route assessment and
        produces actionable safety notes for the transport operation.

        Args:
            assessment: Route assessment dict (from route_assessor).

        Returns:
            List of human-readable safety recommendation strings.
        """
        notes = []

        overall = assessment.get("overall_assessment", {})
        recommendations = assessment.get("recommendations", {})
        traffic = assessment.get("traffic_analysis", {})
        route_compat = assessment.get("route_compatibility", {})

        # From recommendations.for_user
        for_user = recommendations.get("for_user", [])
        for rec in for_user:
            notes.append(rec)

        # Generic safety notes (always included)
        generic = [
            "运输时间建议避开高峰时段（上午7:00-9:00，下午17:00-19:00），减少对交通流的影响",
            "货物固定需定期检查，防止运输过程中出现松动",
            "出发前检查车辆状况（刹车、轮胎、灯光、转向系统）",
            "随车携带应急工具：三角警示牌、灭火器、反光背心、急救包",
            "运输途中开启双闪警示灯，车尾悬挂明显的大件运输标志",
            "安排专人全程监控货物状态，每2小时停车检查一次绑扎情况",
        ]

        # Deduplicate against for_user recommendations.
        # Compare the "stem" (core message with parenthesized details
        # stripped) to avoid counting near-identical notes twice.
        import re

        def _stem(text: str) -> str:
            """Strip parenthesized content for core-message comparison."""
            return re.sub(r'[（(][^）)]*[）)]', '', text).strip()

        for_user_stems = {_stem(r) for r in for_user}
        for g in generic:
            g_stem = _stem(g)
            # Skip if same core message already appears in for_user notes
            if g_stem not in for_user_stems:
                notes.append(g)

        # Weather reminder
        notes.append("出发前关注沿途天气预报，遇恶劣天气（暴雨、大雾、强风）应暂停运输")

        # Structural safety specific notes
        structural = route_compat.get("structural_safety", {})
        risky_bridges = structural.get("high_risk_bridges", 0)
        if risky_bridges > 0:
            notes.append(
                f"途经{risky_bridges}座高风险桥梁，通过时速度不超过30km/h，"
                f"禁止在桥上停车、变道或紧急制动"
            )

        # Tunnel safety
        tunnel_count = assessment.get("tunnel_count", 0)
        if tunnel_count > 3:
            notes.append(
                f"途经{tunnel_count}座隧道，进入隧道前减速至60km/h以下，开启近光灯"
            )

        # Construction zone safety
        construction_impacts = traffic.get("construction_impacts", [])
        if construction_impacts:
            notes.append(
                f"途经{len(construction_impacts)}处施工路段，提前减速，"
                f"严格按施工区域限速标志行驶"
            )

        # Communication
        notes.append(
            "保持与交通管理部门的通讯畅通，遇突发情况立即报告并启动应急预案"
        )

        return notes

    @staticmethod
    def generate_escort_plan(
        vehicle_info: dict,
        risk_level: str,
    ) -> dict:
        """Generate escort vehicle plan based on vehicle dimensions and risk level.

        Per regulation Article 6, category 3 oversized transports must have
        escort vehicles. This method determines the required escort vehicle
        count, configuration, and emergency response plan.

        Args:
            vehicle_info: Vehicle parameters (length, width, height, weight).
            risk_level: Risk level string ("低", "中", "高", "极高").

        Returns:
            Escort plan dict with vehicle count, personnel, and emergency plan.
        """
        length = vehicle_info.get("length", 20.0)
        width = vehicle_info.get("width", 3.0)
        height = vehicle_info.get("height", 4.0)
        weight = vehicle_info.get("total_weight", 49.0)

        # Determine escort vehicle count based on dimension thresholds
        escort_count = 0
        reasons = []

        if length >= ESCORT_THRESHOLDS["length"]:
            escort_count = max(escort_count, 2)
            reasons.append(f"总长{length}m（≥{ESCORT_THRESHOLDS['length']}m）")

        if width >= ESCORT_THRESHOLDS["width"]:
            escort_count = max(escort_count, 2)
            reasons.append(f"总宽{width}m（≥{ESCORT_THRESHOLDS['width']}m）")

        if height >= ESCORT_THRESHOLDS["height"]:
            escort_count = max(escort_count, 1)
            reasons.append(f"总高{height}m（≥{ESCORT_THRESHOLDS['height']}m）")

        if weight >= ESCORT_THRESHOLDS["weight"]:
            escort_count = max(escort_count, 2)
            reasons.append(f"总重{weight}吨（≥{ESCORT_THRESHOLDS['weight']}吨）")

        # Risk level adjustments
        if risk_level == "高":
            escort_count = max(escort_count, 2)
        elif risk_level == "极高":
            escort_count = max(escort_count, 3)

        if escort_count == 0:
            # Minimum escort for any oversized transport
            escort_count = 1
            reasons.append("大件运输标准护送要求")

        # Escort configuration
        if escort_count == 1:
            configuration = "1辆前导车"
            escort_personnel = 2
        elif escort_count == 2:
            configuration = "1辆前导车 + 1辆押尾车"
            escort_personnel = 4
        elif escort_count >= 3:
            configuration = "1辆前导车 + 1辆押尾车 + 1辆机动巡逻车"
            escort_personnel = 6

        # Emergency response plan
        emergency_plan = [
            "车辆故障：立即靠边停车，开启双闪，后方150米设置警示标志，联系维修救援",
            "交通事故：保护现场，救助伤者，立即报警（122）并通知交通保障中心",
            "恶劣天气：就近驶入服务区或紧急停车带，待天气好转后继续行驶",
            "货物移位/松动：立即靠边停车检查，重新绑扎固定后方可继续行驶",
            "桥梁/隧道异常：服从现场管理人员指挥，按应急预案路线绕行",
            "通讯故障：使用备用通讯设备（卫星电话），每30分钟通过沿途收费站报告位置",
        ]

        escort_required = len(reasons) > 0 or risk_level in ("高", "极高")

        return {
            "escort_required": escort_required,
            "escort_vehicle_count": escort_count,
            "configuration": configuration,
            "escort_personnel": escort_personnel,
            "reasons": reasons,
            "emergency_plan": emergency_plan,
        }

    @staticmethod
    def format_for_approver(application: dict) -> str:
        """Format the application as human-readable text for regulator review.

        Produces the "to manager" conversation format as specified in the
        reference workflow document.

        Args:
            application: Complete application dict.

        Returns:
            Formatted text string ready for approver presentation.
        """
        applicant = application.get("applicant", {})
        vc = application.get("vehicle_cargo", {})
        cargo = application.get("cargo", {})
        transport = application.get("transport", {})
        route_analysis = application.get("route_analysis", {})

        lines = []

        # Header
        lines.append("您好，交通保障中心工作人员，现有一条大件运输任务请求，具体信息如下：")

        # Transport basic info
        start = transport.get("origin", "（未填写）")
        end = transport.get("destination", "（未填写）")
        lines.append(f"运输起点：{start}    运输终点：{end}")

        vehicle_type = vc.get("vehicle_type", "（未填写）")
        weight = vc.get("total_weight", "（未填写）")
        lines.append(f"车辆类型：{vehicle_type}    载重：{weight}吨")

        length = vc.get("total_length", "（未填写）")
        width = vc.get("total_width", "（未填写）")
        height = vc.get("total_height", "（未填写）")
        lines.append(f"车辆尺寸：长{length}米，宽{width}米，高{height}米")

        cargo_name = cargo.get("name", "（未填写）")
        cargo_weight = cargo.get("weight", "（未填写）")
        lines.append(f"货物名称及重量：{cargo_name}，{cargo_weight}吨")

        dep_time = transport.get("planned_departure", "（未填写）")
        arr_time = transport.get("estimated_arrival", "（未填写）")
        lines.append(f"计划出发时间：{dep_time}    预计到达时间：{arr_time}")

        lines.append("")

        # Route analysis
        route_desc = route_analysis.get("route_description", "")
        if route_desc:
            lines.append(route_desc)

        # Safety notes
        safety_notes = application.get("safety_notes", [])
        if safety_notes:
            lines.append("安全重点提示：")
            for note in safety_notes[:8]:
                lines.append(f"- {note}")

        lines.append("")

        # Escort plan summary
        escort = application.get("escort_plan", {})
        if escort.get("escort_required"):
            lines.append(
                f"护送方案：需配备{escort.get('escort_vehicle_count', 0)}辆护送车"
                f"（{escort.get('configuration', '')}），"
                f"护送人员{escort.get('escort_personnel', 0)}名。"
            )
            lines.append("")

        # Applicant info summary
        if applicant:
            app_name = applicant.get("name", "")
            app_contact = applicant.get("contact_person", "")
            app_phone = applicant.get("phone", "")
            if app_name:
                lines.append(
                    f"申请人：{app_name}，联系人：{app_contact}，电话：{app_phone}"
                )

        lines.append("")
        lines.append("请交通保障中心根据以上信息，审批并提出具体交通管控建议。")

        return "\n".join(lines)

    @staticmethod
    def to_pdf_data(application: dict) -> dict:
        """Prepare PDF-ready structured data from an application.

        Returns a structured dict that can be consumed by a PDF rendering
        engine (e.g. ReportLab, WeasyPrint, or a frontend PDF generator).
        The dict includes page layout metadata and all content sections.

        Args:
            application: Complete application dict.

        Returns:
            PDF-ready data dict with sections, fonts, and layout info.
        """
        app_id = application.get("application_id", "")
        generated_at = application.get("generated_at", "")

        applicant = application.get("applicant", {})
        vc = application.get("vehicle_cargo", {})
        cargo = application.get("cargo", {})
        transport = application.get("transport", {})
        escort = application.get("escort_plan", {})
        safety_notes = application.get("safety_notes", [])
        compliance = application.get("compliance", {})
        route_analysis = application.get("route_analysis", {})

        return {
            "metadata": {
                "title": f"大件运输许可申请书 - {app_id[:8]}",
                "document_type": "permit_application",
                "application_id": app_id,
                "generated_at": generated_at,
                "version": "1.0",
            },
            "page_setup": {
                "format": "A4",
                "orientation": "portrait",
                "margin_mm": {"top": 25, "bottom": 25, "left": 20, "right": 20},
            },
            "header": {
                "title": "大件运输许可申请书",
                "subtitle": "（依据《超限运输车辆行驶公路管理规定》第六条）",
                "application_id": f"编号：{app_id[:8]}",
                "date": generated_at[:10] if generated_at else "",
            },
            "sections": [
                {
                    "heading": "一、申请人信息",
                    "fields": [
                        {"label": "单位名称", "value": applicant.get("name", "")},
                        {"label": "单位地址", "value": applicant.get("address", "")},
                        {"label": "联系人", "value": applicant.get("contact_person", "")},
                        {"label": "联系电话", "value": applicant.get("phone", "")},
                        {"label": "证件号码", "value": applicant.get("id_number", "")},
                    ],
                },
                {
                    "heading": "二、车货信息",
                    "fields": [
                        {"label": "车辆类型", "value": vc.get("vehicle_type", "")},
                        {"label": "车货总长度（米）", "value": str(vc.get("total_length", ""))},
                        {"label": "车货总宽度（米）", "value": str(vc.get("total_width", ""))},
                        {"label": "车货总高度（米）", "value": str(vc.get("total_height", ""))},
                        {"label": "车货总质量（吨）", "value": str(vc.get("total_weight", ""))},
                        {"label": "总轴数", "value": str(vc.get("axle_count", ""))},
                        {"label": "轴距（米）", "value": vc.get("axle_spacings_str", "")},
                        {"label": "轴荷（吨）", "value": vc.get("axle_loads_str", "")},
                    ],
                },
                {
                    "heading": "三、货物信息",
                    "fields": [
                        {"label": "货物名称", "value": cargo.get("name", "")},
                        {"label": "货物尺寸（米）", "value": cargo.get("dimensions_str", "")},
                        {"label": "货物重量（吨）", "value": str(cargo.get("weight", ""))},
                    ],
                },
                {
                    "heading": "四、运输信息",
                    "fields": [
                        {"label": "运输起点", "value": transport.get("origin", "")},
                        {"label": "运输终点", "value": transport.get("destination", "")},
                        {"label": "通行路线", "value": transport.get("route_text", "")},
                        {"label": "计划出发时间", "value": transport.get("planned_departure", "")},
                        {"label": "预计到达时间", "value": transport.get("estimated_arrival", "")},
                        {"label": "运输距离（公里）", "value": str(transport.get("distance_km", ""))},
                    ],
                },
                {
                    "heading": "五、护送方案（三类大件运输必需）",
                    "fields": [
                        {"label": "护送车辆数", "value": str(escort.get("escort_vehicle_count", ""))},
                        {"label": "护送车辆配置", "value": escort.get("configuration", "")},
                        {"label": "护送人员数", "value": str(escort.get("escort_personnel", ""))},
                    ],
                    "subsections": [
                        {
                            "heading": "应急预案",
                            "items": escort.get("emergency_plan", []),
                        }
                    ],
                },
            ],
            "footer": {
                "approval_line": "审批意见：________________________________",
                "approval_date": "日期：________________",
                "stamp_area": "（审批单位盖章）",
            },
            "annex": {
                "heading": "附录：安全重点提示",
                "items": safety_notes,
            },
        }

    # ── Internal helpers ──

    @staticmethod
    def _build_applicant_section(info: dict) -> dict:
        """Build normalized applicant info section."""
        return {
            "name": info.get("name", ""),
            "address": info.get("address", ""),
            "contact_person": info.get("contact_person", ""),
            "phone": info.get("phone", ""),
            "id_number": info.get("id_number", ""),
        }

    @staticmethod
    def _build_vehicle_cargo_section(
        vehicle_info: dict, cargo_info: dict
    ) -> dict:
        """Build combined vehicle + cargo info section."""
        axle_spacings = vehicle_info.get("axle_spacings", [])
        axle_loads = vehicle_info.get("axle_loads", [])

        return {
            "vehicle_type": vehicle_info.get("vehicle_type", ""),
            "total_length": vehicle_info.get("length", 0),
            "total_width": vehicle_info.get("width", 0),
            "total_height": vehicle_info.get("height", 0),
            "total_weight": vehicle_info.get("total_weight", 0),
            "axle_count": vehicle_info.get("axle_count", 0),
            "axle_spacings": axle_spacings,
            "axle_spacings_str": ", ".join(str(s) for s in axle_spacings) if axle_spacings else "",
            "axle_loads": axle_loads,
            "axle_loads_str": ", ".join(str(l) for l in axle_loads) if axle_loads else "",
            "tractor_length": vehicle_info.get("tractor_length"),
            "trailer_length": vehicle_info.get("trailer_length"),
            "tractor_axle_count": vehicle_info.get("tractor_axle_count"),
            "trailer_axle_count": vehicle_info.get("trailer_axle_count"),
            "first_axle_distance": vehicle_info.get("first_axle_distance"),
        }

    @staticmethod
    def _build_cargo_section(cargo_info: dict) -> dict:
        """Build cargo info section."""
        cargo_len = cargo_info.get("length", 0)
        cargo_width = cargo_info.get("width", 0)
        cargo_height = cargo_info.get("height", 0)
        dimensions_parts = []
        if cargo_len:
            dimensions_parts.append(str(cargo_len))
        if cargo_width:
            dimensions_parts.append(str(cargo_width))
        if cargo_height:
            dimensions_parts.append(str(cargo_height))

        return {
            "name": cargo_info.get("name", ""),
            "length": cargo_len,
            "width": cargo_width,
            "height": cargo_height,
            "weight": cargo_info.get("weight", 0),
            "dimensions_str": " x ".join(dimensions_parts) + " 米" if dimensions_parts else "",
        }

    @staticmethod
    def _build_transport_section(
        route_data: dict,
        vehicle_info: dict,
        schedule_info: Optional[dict] = None,
    ) -> dict:
        """Build transport plan section."""
        routes = route_data.get("routes", [])
        first_route = routes[0] if routes else {}

        # Determine origin/destination from route description
        origin = route_data.get("origin", "")
        destination = route_data.get("destination", "")
        if not origin and not destination:
            desc = first_route.get("route_description", "")
            parts = desc.split("--")
            if len(parts) >= 2:
                origin = parts[0].strip()
                destination = parts[-1].strip()

        schedule = schedule_info or {}
        now = datetime.now()

        dep_time = schedule.get("departure_time")
        if isinstance(dep_time, datetime):
            dep_time_str = dep_time.strftime("%Y年%m月%d日%H点")
        elif isinstance(dep_time, str):
            dep_time_str = dep_time
        else:
            dep_time_str = now.strftime("%Y年%m月%d日%H点")

        arr_time = schedule.get("estimated_arrival")
        if isinstance(arr_time, datetime):
            arr_time_str = arr_time.strftime("%Y年%m月%d日%H点")
        elif isinstance(arr_time, str):
            arr_time_str = arr_time
        else:
            # Estimate arrival from route duration
            duration_sec = first_route.get("duration", 0)
            est_arrival = now + timedelta(seconds=duration_sec)
            arr_time_str = est_arrival.strftime("%Y年%m月%d日%H点")

        # Build route text string
        route_text = first_route.get("route_description", "")

        return {
            "origin": origin,
            "destination": destination,
            "route_text": route_text,
            "planned_departure": dep_time_str,
            "estimated_arrival": arr_time_str,
            "distance_meters": first_route.get("distance", 0),
            "distance_km": round(first_route.get("distance", 0) / 1000, 1),
            "duration_seconds": first_route.get("duration", 0),
            "duration_minutes": first_route.get("duration", 0) // 60,
        }

    @staticmethod
    def _determine_risk_level(
        vehicle_info: dict, assessment: dict
    ) -> str:
        """Determine risk level from assessment or vehicle dimensions."""
        # Prefer assessment-based risk level
        overall = assessment.get("overall_assessment", {})
        risk_level = overall.get("risk_level", "")
        if risk_level:
            return risk_level

        # Fallback: compute from vehicle dimensions
        length = vehicle_info.get("length", 20.0)
        width = vehicle_info.get("width", 3.0)
        height = vehicle_info.get("height", 4.0)
        weight = vehicle_info.get("total_weight", 49.0)

        risk_score = 0
        if length >= 30:
            risk_score += 2
        elif length >= 22:
            risk_score += 1

        if width >= 4.5:
            risk_score += 2
        elif width >= 3.75:
            risk_score += 1

        if height >= 5.0:
            risk_score += 2
        elif height >= 4.5:
            risk_score += 1

        if weight >= 150:
            risk_score += 2
        elif weight >= 100:
            risk_score += 1

        if risk_score >= 6:
            return "极高"
        elif risk_score >= 4:
            return "高"
        elif risk_score >= 2:
            return "中"
        return "低"

    @staticmethod
    def _format_route_entry(
        route: dict, idx: int, is_primary: bool
    ) -> dict:
        """Format a single route entry for the route analysis section."""
        distance_km = round(route.get("distance", 0) / 1000, 1)
        duration_min = route.get("duration", 0) // 60

        return {
            "index": idx,
            "is_primary": is_primary,
            "route_description": route.get("route_description", ""),
            "distance_km": distance_km,
            "duration_minutes": duration_min,
            "major_roads": route.get("major_roads", []),
            "tunnel_count": route.get("tunnel_count", 0),
            "toll_cost": route.get("toll_cost", 0),
            "pros": route.get("pros", []),
            "cons": route.get("cons", []),
        }

    @staticmethod
    def _build_compliance_summary(
        vehicle_info: dict,
        assessment: dict,
        risk_level: str,
    ) -> dict:
        """Build a compliance summary section."""
        length = vehicle_info.get("length", 0)
        width = vehicle_info.get("width", 0)
        height = vehicle_info.get("height", 0)
        weight = vehicle_info.get("total_weight", 0)

        # Dimension compliance checks
        checks = []
        all_compliant = True

        if height > 5.0:
            checks.append({"item": "高度", "status": "超标", "detail": f"{height}m > 5.0m限高"})
            all_compliant = False
        elif height > 4.5:
            checks.append({"item": "高度", "status": "临界", "detail": f"{height}m 接近限高5.0m"})
        else:
            checks.append({"item": "高度", "status": "合规", "detail": f"{height}m"})

        if width > 5.0:
            checks.append({"item": "宽度", "status": "超标", "detail": f"{width}m > 5.0m限制"})
            all_compliant = False
        elif width > 3.75:
            checks.append({"item": "宽度", "status": "需审批", "detail": f"{width}m 超过标准车道3.75m"})
        else:
            checks.append({"item": "宽度", "status": "合规", "detail": f"{width}m"})

        if length > 35.0:
            checks.append({"item": "长度", "status": "超标", "detail": f"{length}m > 35.0m限制"})
            all_compliant = False
        elif length > 28.0:
            checks.append({"item": "长度", "status": "需审批", "detail": f"{length}m 超过28m需护送"})
        else:
            checks.append({"item": "长度", "status": "合规", "detail": f"{length}m"})

        if weight > 200.0:
            checks.append({"item": "重量", "status": "超标", "detail": f"{weight}吨 > 200吨限制"})
            all_compliant = False
        elif weight > 100.0:
            checks.append({"item": "重量", "status": "需审批", "detail": f"{weight}吨 超过100吨需护送"})
        elif weight > 55.0:
            checks.append({"item": "重量", "status": "需审批", "detail": f"{weight}吨 超过55吨需许可"})
        else:
            checks.append({"item": "重量", "status": "合规", "detail": f"{weight}吨"})

        overall_status = "符合要求" if all_compliant else "需特别审批"

        return {
            "overall_status": overall_status,
            "risk_level": risk_level,
            "dimension_checks": checks,
            "assessment_recommendation": assessment.get(
                "overall_assessment", {}
            ).get("recommendation", "未评估"),
            "assessment_score": assessment.get(
                "overall_assessment", {}
            ).get("score", None),
        }


# Singleton
permit_generator = PermitGenerator()
