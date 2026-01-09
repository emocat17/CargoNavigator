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
    departure_time: Optional[str] = Field(None, description="预计出发时间 (ISO format)")

class TMC(BaseModel):
    distance: int
    status: str
    polyline: str

class RouteStep(BaseModel):
    instruction: str
    distance: int
    duration: int
    polyline: str
    road: str = ""
    action: str = ""
    assistant_action: str = ""
    tmcs: List[TMC] = []
    traffic_status: str = "未知" # 畅通, 缓行, 拥堵, 未知

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
    traffic_condition: str = "未知"
    major_roads: List[str] = []
    passed_cities: List[str] = []
    toll_roads_details: List[str] = []
    tunnel_count: int = 0
    tunnel_distance: int = 0
    estimated_fuel_cost: float = 0.0
    total_cost: float = 0.0
    tags: List[str] = []


class RoutePlanResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Dict[str, List[RouteInfo]]
