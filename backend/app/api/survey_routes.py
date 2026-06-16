"""
Digital Road Survey API Endpoints.

Provides:
- POST /survey/generate - Generate pre-trip road survey checklist
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.shared import VehicleInfoInput, RouteDataInput
from app.services.road_surveyor import road_surveyor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Road Survey"])


class BridgeAssessmentInput(BaseModel):
    """Pre-computed bridge assessment result (optional)."""
    overall_safe: Optional[bool] = Field(None, description="总体安全性")
    risk_level: Optional[str] = Field(None, description="风险等级")
    total_bridges_on_route: Optional[int] = Field(None, description="沿线桥梁总数")
    bridges_evaluated: Optional[int] = Field(None, description="已评估桥梁数")
    passable_bridges: Optional[int] = Field(None, description="可通行桥梁数")
    risky_bridges: Optional[int] = Field(None, description="风险桥梁数")
    max_effect_ratio: Optional[float] = Field(None, description="最大效应比值")
    bridge_details: Optional[list[dict]] = Field(default_factory=list, description="桥梁详情列表")
    route_highways: Optional[list[str]] = Field(default_factory=list, description="路线涉及的高速")
    route_level_restrictions: Optional[dict] = Field(default_factory=dict, description="路线级限制")
    warnings: Optional[list[str]] = Field(default_factory=list, description="警告信息")
    recommendations: Optional[list[str]] = Field(default_factory=list, description="建议")


class SurveyGenerateRequest(BaseModel):
    """Request body for survey checklist generation."""
    route_data: RouteDataInput = Field(..., description="路线数据")
    vehicle_info: VehicleInfoInput = Field(..., description="车辆信息")
    bridge_assessment: Optional[BridgeAssessmentInput] = Field(
        None, description="桥梁评估结果（可选，含效应比值用于风险排序）"
    )


class SurveyResponse(BaseModel):
    """Standard API response wrapper."""
    code: int = 200
    msg: str = "success"
    data: dict = {}


# ── Endpoints ──

@router.post("/survey/generate", response_model=SurveyResponse)
async def generate_survey_checklist(request: SurveyGenerateRequest):
    """Generate a pre-trip road survey checklist.

    Combines route data, vehicle dimensions, and optional bridge assessment
    to produce a prioritized checklist of checkpoints that surveyors must
    physically verify before oversized cargo transport.

    The checklist covers five categories:
    - Bridges (sorted by risk, highest effect ratio first)
    - Tunnels (height/width check points)
    - Toll stations (wide-load lane verification)
    - Interchange ramps (turning radius check points)
    - Overhead obstacles (gantry signs, ETC frames, power lines)

    Example request:
    ```json
    {
        "route_data": {
            "id": "route_1",
            "route_description": "G1517莆炎高速(36km→395km) → G15沈海高速(2130km→2323km) → S53(0km→7km)",
            "major_roads": ["G1517莆炎高速", "G15沈海高速", "S53"],
            "distance": 285000,
            "duration": 14400,
            "tunnel_count": 53,
            "tunnel_distance": 45200
        },
        "vehicle_info": {
            "length": 24.0,
            "width": 4.9,
            "height": 4.7,
            "total_weight": 150.0,
            "axis_weight": 18.0,
            "axis_count": 8,
            "axis_loads": [18.0, 18.0, 19.0, 19.0, 19.0, 19.0, 19.0, 19.0],
            "axis_spacings": [3.5, 1.5, 3.0, 3.0, 3.0, 3.0, 3.0]
        },
        "bridge_assessment": null
    }
    ```
    """
    try:
        # Convert Pydantic models to plain dicts
        route_dict = request.route_data.model_dump(exclude_none=True)
        vehicle_dict = request.vehicle_info.model_dump(exclude_none=True)
        assessment_dict = (
            request.bridge_assessment.model_dump(exclude_none=True)
            if request.bridge_assessment
            else None
        )

        result = road_surveyor.generate_checklist(
            route_data=route_dict,
            vehicle_info=vehicle_dict,
            bridge_assessment=assessment_dict,
        )

        return SurveyResponse(data=result)
    except Exception as e:
        logger.exception(f"Survey checklist generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"勘测清单生成失败: {str(e)}"
        )
