"""
Route Assessment API Endpoints.

Provides:
- POST /routes/assess   - Single route comprehensive assessment
- POST /routes/compare  - Multi-route comparison and ranking
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.route_assessor import route_assessor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Route Assessment"])


# ── Request/Response models ──

class VehicleInfoInput(BaseModel):
    """Vehicle parameters for route assessment."""
    length: float = Field(..., description="车长 (米)", ge=0)
    width: float = Field(..., description="车宽 (米)", ge=0)
    height: float = Field(..., description="车高 (米)", ge=0)
    weight: float = Field(..., description="车货总重 (吨)", ge=0)
    axis_weight: Optional[float] = Field(None, description="最大轴重 (吨)")
    axis_count: Optional[int] = Field(None, description="轴数", ge=1)
    axis_loads: Optional[list[float]] = Field(None, description="各轴载荷分布 (吨)")
    axis_spacings: Optional[list[float]] = Field(None, description="各轴间距 (米)")


class RouteDataInput(BaseModel):
    """Route data input for assessment. Accepts fields from the Amap
    RouteInfo model, but all fields are optional for flexibility."""
    id: Optional[str] = Field(None, description="路线ID")
    route_description: Optional[str] = Field("", description="路线描述 (如: 北村--G76--海沧)")
    major_roads: Optional[list[str]] = Field(default_factory=list, description="主要道路列表")
    distance: Optional[int] = Field(0, description="总距离 (米)")
    duration: Optional[int] = Field(0, description="预计时间 (秒)")
    tunnel_count: Optional[int] = Field(0, description="隧道数量")
    tunnel_distance: Optional[int] = Field(0, description="隧道总长 (米)")
    toll_cost: Optional[float] = Field(0.0, description="过路费 (元)")
    traffic_condition: Optional[str] = Field("", description="路况描述")
    risk_warnings: Optional[list[str]] = Field(default_factory=list, description="风险警告")
    strategy: Optional[str] = Field("", description="选路策略")


class RouteAssessRequest(BaseModel):
    """Request body for single route assessment."""
    route_data: RouteDataInput = Field(..., description="路线数据")
    vehicle_info: VehicleInfoInput = Field(..., description="车辆信息")


class RouteCompareRequest(BaseModel):
    """Request body for multi-route comparison."""
    routes: list[RouteDataInput] = Field(..., description="多条路线数据", min_length=1, max_length=10)
    vehicle_info: VehicleInfoInput = Field(..., description="车辆信息")


class AssessResponse(BaseModel):
    """Standard API response wrapper."""
    code: int = 200
    msg: str = "success"
    data: dict = {}


# ── Endpoints ──

@router.post("/routes/assess", response_model=AssessResponse)
async def assess_route(request: RouteAssessRequest):
    """Perform comprehensive assessment of a single route.

    Combines bridge safety analysis, construction/traffic event matching,
    and vehicle dimension compliance checks into a scored assessment
    with structured recommendations.

    Example request:
    ```json
    {
        "route_data": {
            "id": "route_1",
            "route_description": "北村--G76--天宝--G76--陈巷--G76--海沧",
            "major_roads": ["G76厦蓉高速"],
            "distance": 85000,
            "duration": 11700,
            "tunnel_count": 5
        },
        "vehicle_info": {
            "length": 24.0,
            "width": 4.9,
            "height": 4.7,
            "weight": 150.0,
            "axis_weight": 18.0,
            "axis_count": 8
        }
    }
    ```
    """
    try:
        # Convert Pydantic models to plain dicts for the service
        route_dict = request.route_data.model_dump(exclude_none=True)
        vehicle_dict = request.vehicle_info.model_dump(exclude_none=True)

        result = route_assessor.assess_route(route_dict, vehicle_dict)

        return AssessResponse(data=result)
    except Exception as e:
        logger.exception(f"Route assessment failed: {e}")
        raise HTTPException(status_code=500, detail=f"路线评估失败: {str(e)}")


@router.post("/routes/compare", response_model=AssessResponse)
async def compare_routes(request: RouteCompareRequest):
    """Compare multiple routes and rank them by safety and feasibility.

    Each route is independently assessed, then ranked by composite score.
    Returns the best route recommendation along with detailed comparison.

    Example request:
    ```json
    {
        "routes": [
            {
                "id": "route_1",
                "route_description": "北村--G76--海沧",
                "major_roads": ["G76厦蓉高速"],
                "distance": 85000,
                "duration": 11700
            },
            {
                "id": "route_2",
                "route_description": "北村--G15--海沧",
                "major_roads": ["G15沈海高速"],
                "distance": 92000,
                "duration": 12600
            }
        ],
        "vehicle_info": {
            "length": 24.0,
            "width": 4.9,
            "height": 4.7,
            "weight": 150.0,
            "axis_weight": 18.0,
            "axis_count": 8
        }
    }
    ```
    """
    try:
        route_dicts = [r.model_dump(exclude_none=True) for r in request.routes]
        vehicle_dict = request.vehicle_info.model_dump(exclude_none=True)

        result = route_assessor.compare_routes(route_dicts, vehicle_dict)

        return AssessResponse(data=result)
    except Exception as e:
        logger.exception(f"Route comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"路线比较失败: {str(e)}")
