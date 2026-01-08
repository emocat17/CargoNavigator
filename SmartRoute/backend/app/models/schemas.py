from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class VehicleInfo(BaseModel):
    length: float = Field(..., description="车长 (米)")
    width: float = Field(..., description="车宽 (米)")
    height: float = Field(..., description="车高 (米)")
    weight: float = Field(..., description="车货总重 (吨)")
    axis_weight: float = Field(..., description="轴重 (吨)")

class RoutePlanRequest(BaseModel):
    origin: str = Field(..., description="起点 (地址或经纬度)")
    destination: str = Field(..., description="终点 (地址或经纬度)")
    vehicle: Optional[VehicleInfo] = None
    strategy: int = Field(0, description="选路策略")

class RouteStep(BaseModel):
    instruction: str
    distance: int
    duration: int
    polyline: str

class RouteInfo(BaseModel):
    id: str
    distance: int
    duration: int
    path_points: str 
    steps: List[RouteStep]
    toll_distance: int = 0
    toll_cost: float = 0.0
    traffic_lights: int = 0
    strategy: str = ""
    restriction: int = 0

class RoutePlanResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Dict[str, List[RouteInfo]]
