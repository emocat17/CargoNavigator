from pydantic import BaseModel, Field
from typing import List, Optional

class VehicleProfileBase(BaseModel):
    name: str = Field(..., description="车辆档案名称，如'150吨液压轴线车'")
    license_plate: Optional[str] = Field(None, description="车牌号")
    length: float = Field(..., gt=0, description="车长(米)")
    width: float = Field(..., gt=0, description="车宽(米)")
    height: float = Field(..., gt=0, description="车高(米)")
    total_weight: float = Field(..., gt=0, description="车货总重(吨)")
    
    axis_count: int = Field(..., gt=0, description="轴数")
    axis_weights: List[float] = Field(..., description="轴重分布(吨)，如 [10, 10, 17.98]")
    axis_distances: List[float] = Field(..., description="轴距分布(米)，如 [3.2, 1.4]")
    
    tire_count: Optional[int] = Field(None, description="轮胎数")
    cargo_type: Optional[str] = Field(None, description="货物类型")

class VehicleProfileCreate(VehicleProfileBase):
    pass

class VehicleProfileUpdate(BaseModel):
    name: Optional[str] = None
    license_plate: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    total_weight: Optional[float] = None
    axis_count: Optional[int] = None
    axis_weights: Optional[List[float]] = None
    axis_distances: Optional[List[float]] = None
    tire_count: Optional[int] = None
    cargo_type: Optional[str] = None

class VehicleProfileResponse(VehicleProfileBase):
    id: str

    class Config:
        from_attributes = True
