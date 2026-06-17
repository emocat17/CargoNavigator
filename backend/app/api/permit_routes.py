"""
Permit Application API Endpoints.

Provides:
- POST /permit/generate  - Generate complete permit application
- POST /permit/preview   - Preview application text for approver
- GET  /permit/export/{app_id} - Export application data
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.shared import VehicleInfoInput
from app.services.permit_generator import permit_generator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Permit Application"])

# 保留 CargoInfoInput 和 ApplicantInfoInput —— 它们不是共享的
# VehicleInfoInput 已从 shared 导入


class CargoInfoInput(BaseModel):
    """Cargo information for permit application."""
    name: str = Field(..., description="货物名称")
    length: Optional[float] = Field(0, description="货物长度 (米)")
    width: Optional[float] = Field(0, description="货物宽度 (米)")
    height: Optional[float] = Field(0, description="货物高度 (米)")
    weight: Optional[float] = Field(0, description="货物重量 (吨)")


class ApplicantInfoInput(BaseModel):
    """Applicant information per regulation Article 6."""
    name: Optional[str] = Field("", description="申请单位名称")
    address: Optional[str] = Field("", description="单位地址")
    contact_person: Optional[str] = Field("", description="联系人")
    phone: Optional[str] = Field("", description="联系电话")
    id_number: Optional[str] = Field("", description="证件号码")


class ScheduleInfoInput(BaseModel):
    """Schedule information for the transport."""
    departure_time: Optional[str] = Field(None, description="计划出发时间")
    estimated_arrival: Optional[str] = Field(None, description="预计到达时间")


class RouteEntryInput(BaseModel):
    """A single route entry for permit application."""
    id: Optional[str] = Field(None, description="路线ID")
    route_description: Optional[str] = Field("", description="路线描述 (如: 北村--G76--海沧)")
    major_roads: Optional[list[str]] = Field(default_factory=list, description="主要道路")
    distance: Optional[int] = Field(0, description="距离 (米)")
    duration: Optional[int] = Field(0, description="预计时间 (秒)")
    tunnel_count: Optional[int] = Field(0, description="隧道数量")
    tunnel_distance: Optional[int] = Field(0, description="隧道总长 (米)")
    toll_cost: Optional[float] = Field(0.0, description="过路费 (元)")
    pros: Optional[list[str]] = Field(default_factory=list, description="优点列表")
    cons: Optional[list[str]] = Field(default_factory=list, description="缺点列表")


class AssessmentInput(BaseModel):
    """Assessment data input (from route_assessor, all fields optional)."""
    overall_assessment: Optional[dict] = Field(default_factory=dict, description="总览评估")
    traffic_analysis: Optional[dict] = Field(default_factory=dict, description="交通分析")
    route_compatibility: Optional[dict] = Field(default_factory=dict, description="路线兼容性")
    recommendations: Optional[dict] = Field(default_factory=dict, description="建议")


class PermitGenerateRequest(BaseModel):
    """Request body for permit application generation."""
    routes: list[RouteEntryInput] = Field(
        ..., description="路线列表（至少1条）", min_length=1, max_length=10
    )
    vehicle_info: VehicleInfoInput = Field(..., description="车辆信息")
    cargo_info: CargoInfoInput = Field(..., description="货物信息")
    applicant_info: Optional[ApplicantInfoInput] = Field(
        default=None, description="申请人信息"
    )
    schedule_info: Optional[ScheduleInfoInput] = Field(
        default=None, description="运输时间计划"
    )
    assessment: Optional[AssessmentInput] = Field(
        default=None, description="路线评估结果（可选）"
    )


class PermitPreviewRequest(BaseModel):
    """Request body for application text preview."""
    routes: list[RouteEntryInput] = Field(
        ..., description="路线列表（至少1条）", min_length=1, max_length=10
    )
    vehicle_info: VehicleInfoInput = Field(..., description="车辆信息")
    cargo_info: CargoInfoInput = Field(..., description="货物信息")
    applicant_info: Optional[ApplicantInfoInput] = Field(
        default=None, description="申请人信息"
    )
    schedule_info: Optional[ScheduleInfoInput] = Field(
        default=None, description="运输时间计划"
    )
    assessment: Optional[AssessmentInput] = Field(
        default=None, description="路线评估结果（可选）"
    )


# ── Response models ──

class PermitResponse(BaseModel):
    """Standard API response wrapper."""
    code: int = 200
    msg: str = "success"
    data: dict = {}


class PermitPreviewResponse(BaseModel):
    """Response for application text preview."""
    code: int = 200
    msg: str = "success"
    data: dict = {}
    formatted_text: str = ""


class PermitExportResponse(BaseModel):
    """Response for application export."""
    code: int = 200
    msg: str = "success"
    data: dict = {}


# ── Endpoints ──

@router.post("/permit/generate", response_model=PermitResponse)
async def generate_permit(request: PermitGenerateRequest):
    """Generate a complete oversized cargo transport permit application.

    Combines vehicle info, cargo info, applicant info, schedule, and routes
    with assessments to produce a comprehensive permit application document
    ready for regulator review.

    All fields required by regulation Article 6 are included:
    - Applicant information (name, address, contact, ID)
    - Vehicle + cargo combined dimensions and weights
    - Cargo details
    - Transport plan (origin, destination, route, timing)
    - Escort plan (for category 3 transports)
    - Safety notes and compliance summary

    Example request:
    ```json
    {
        "routes": [
            {
                "id": "route_1",
                "route_description": "北村--G76厦蓉高速--海沧",
                "major_roads": ["G76厦蓉高速"],
                "distance": 85000,
                "duration": 11700,
                "tunnel_count": 5,
                "pros": ["路况良好", "限高限宽满足条件"],
                "cons": ["某转弯处需安排交警疏导"]
            },
            {
                "id": "route_2",
                "route_description": "北村--G15沈海高速--G76厦蓉高速--海沧",
                "major_roads": ["G15沈海高速", "G76厦蓉高速"],
                "distance": 92000,
                "duration": 12600,
                "pros": ["全程高速，路况稳定"],
                "cons": ["里程较长，预计增加30分钟"]
            }
        ],
        "vehicle_info": {
            "vehicle_type": "牵引车+低平板半挂车",
            "length": 24.0,
            "width": 4.9,
            "height": 4.7,
            "weight": 150.0,
            "axle_count": 8,
            "axle_loads": [18.0, 18.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0],
            "axle_spacings": [3.5, 1.5, 3.0, 3.0, 3.0, 3.0, 3.0]
        },
        "cargo_info": {
            "name": "变压器",
            "length": 10.0,
            "width": 4.5,
            "height": 4.2,
            "weight": 120.0
        },
        "applicant_info": {
            "name": "XX大件运输有限公司",
            "address": "XX省XX市XX区XX路XX号",
            "contact_person": "张三",
            "phone": "13800138000",
            "id_number": "请填写统一社会信用代码"
        },
        "schedule_info": {
            "departure_time": "2025年6月20日8点",
            "estimated_arrival": "2025年6月20日12点"
        }
    }
    ```
    """
    try:
        # Convert Pydantic models to plain dicts
        route_dicts = [r.model_dump(exclude_none=True) for r in request.routes]
        vehicle_dict = request.vehicle_info.model_dump(exclude_none=True)
        cargo_dict = request.cargo_info.model_dump(exclude_none=True)
        applicant_dict = (
            request.applicant_info.model_dump(exclude_none=True)
            if request.applicant_info
            else {}
        )
        schedule_dict = (
            request.schedule_info.model_dump(exclude_none=True)
            if request.schedule_info
            else {}
        )
        assessment_dict = (
            request.assessment.model_dump(exclude_none=True)
            if request.assessment
            else {}
        )

        route_data = {
            "routes": route_dicts,
            "assessment": assessment_dict,
        }

        result = permit_generator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle_dict,
            cargo_info=cargo_dict,
            applicant_info=applicant_dict,
            schedule_info=schedule_dict,
        )

        return PermitResponse(data=result)
    except Exception as e:
        logger.exception(f"Permit generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"许可申请书生成失败: {str(e)}"
        )


@router.post("/permit/preview")
async def preview_permit(request: PermitPreviewRequest):
    """Preview the formatted application text as it would appear to the approver.

    Returns both the structured application data and the human-readable
    formatted text string suitable for regulator review.

    This endpoint mirrors /permit/generate but additionally returns
    the 'formatted_text' field containing the "to manager" conversation
    format text.
    """
    try:
        route_dicts = [r.model_dump(exclude_none=True) for r in request.routes]
        vehicle_dict = request.vehicle_info.model_dump(exclude_none=True)
        cargo_dict = request.cargo_info.model_dump(exclude_none=True)
        applicant_dict = (
            request.applicant_info.model_dump(exclude_none=True)
            if request.applicant_info
            else {}
        )
        schedule_dict = (
            request.schedule_info.model_dump(exclude_none=True)
            if request.schedule_info
            else {}
        )
        assessment_dict = (
            request.assessment.model_dump(exclude_none=True)
            if request.assessment
            else {}
        )

        route_data = {
            "routes": route_dicts,
            "assessment": assessment_dict,
        }

        application = permit_generator.generate_application(
            route_data=route_data,
            vehicle_info=vehicle_dict,
            cargo_info=cargo_dict,
            applicant_info=applicant_dict,
            schedule_info=schedule_dict,
        )

        formatted_text = permit_generator.format_for_approver(application)

        return {
            "code": 200,
            "msg": "success",
            "data": application,
            "formatted_text": formatted_text,
        }
    except Exception as e:
        logger.exception(f"Permit preview failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"许可申请书预览失败: {str(e)}"
        )


@router.get("/permit/export/{app_id}")
async def export_permit(app_id: str):
    """Export permit application data for a given application ID.

    Returns the PDF-ready structured data that can be consumed by a
    PDF rendering engine (ReportLab, WeasyPrint, or frontend PDF lib).

    For now, this generates a fresh application with placeholder data
    since we don't have persistent storage for generated permits yet.
    In production, this would retrieve the stored application by ID.

    Args:
        app_id: The application ID to export.
    """
    try:
        # In a full implementation, this would fetch from a database.
        # For now, return a structured placeholder indicating the app ID.
        # The frontend can use this to render/export the application.

        # Generate a placeholder application for demonstration
        demo_vehicle = {
            "vehicle_type": "牵引车+低平板半挂车",
            "length": 24.0,
            "width": 4.9,
            "height": 4.7,
            "weight": 150.0,
            "axle_count": 8,
        }
        demo_cargo = {
            "name": "大型变压器",
            "length": 10.0,
            "width": 4.5,
            "height": 4.2,
            "weight": 120.0,
        }
        demo_routes = [
            {
                "route_description": "北村--G76厦蓉高速--海沧",
                "major_roads": ["G76厦蓉高速"],
                "distance": 85000,
                "duration": 11700,
            }
        ]

        application = permit_generator.generate_application(
            route_data={"routes": demo_routes, "assessment": {}},
            vehicle_info=demo_vehicle,
            cargo_info=demo_cargo,
        )
        application["application_id"] = app_id

        pdf_data = permit_generator.to_pdf_data(application)

        return {
            "code": 200,
            "msg": "success",
            "data": pdf_data,
        }
    except Exception as e:
        logger.exception(f"Permit export failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"许可申请书导出失败: {str(e)}"
        )
