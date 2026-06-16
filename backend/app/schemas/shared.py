"""
共享请求模型 —— 所有 API 路由从这里引用，确保字段名一致。

统一字段名约定：
- total_weight: 车货总重（吨）
- axis_weight: 最大轴重（吨）
- axis_count: 轴数
- axis_loads:  各轴载荷分布（吨）
- axis_spacings: 各轴间距（米）
"""

from typing import Optional

from pydantic import BaseModel, Field


class VehicleInfoInput(BaseModel):
    """车辆信息 —— 所有路由共用的统一模型。

    POST /routes/assess, /routes/compare, /survey/generate,
         /permit/generate, /permit/preview 都使用此模型。
    """

    length: float = Field(..., description="车货总长 (米)", ge=0)
    width: float = Field(..., description="车货总宽 (米)", ge=0)
    height: float = Field(..., description="车货总高 (米)", ge=0)
    total_weight: float = Field(..., description="车货总重 (吨)", ge=0)
    axis_weight: Optional[float] = Field(None, description="最大轴重 (吨)")
    axis_count: Optional[int] = Field(None, description="总轴数", ge=1)
    axis_loads: Optional[list[float]] = Field(None, description="各轴载荷分布 (吨)")
    axis_spacings: Optional[list[float]] = Field(None, description="各轴间距 (米)")
    trailer_type: Optional[str] = Field(None, description="挂车类型 (lowbed / hydraulic)")
    # 以下为许可申请用到但评估/勘测会忽略的字段
    vehicle_type: Optional[str] = Field(None, description="车辆类型描述")
    tractor_length: Optional[float] = Field(None, description="牵引车长度 (米)")
    trailer_length: Optional[float] = Field(None, description="挂车长度 (米)")
    tractor_axle_count: Optional[int] = Field(None, description="牵引车轴数")
    trailer_axle_count: Optional[int] = Field(None, description="挂车轴数")
    first_axle_distance: Optional[float] = Field(None, description="车头距第一轴中心距离 (米)")


class RouteDataInput(BaseModel):
    """路线数据 —— 所有路由共用的统一模型。"""

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
