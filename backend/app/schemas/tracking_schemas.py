"""
Pydantic schemas for tracking API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class TransportOrderCreate(BaseModel):
    """Request to create a transport order."""
    application_id: Optional[str] = None
    route_data: Optional[dict] = Field(default_factory=dict, description="路线数据")
    vehicle_info: Optional[dict] = Field(default_factory=dict, description="车辆信息")
    assessment_data: Optional[dict] = Field(default_factory=dict, description="评估数据")
    notes: Optional[str] = None
    attachments: Optional[List[dict]] = Field(default_factory=list, description="附件列表")


class StatusUpdateRequest(BaseModel):
    """Request to update order status."""
    new_status: str = Field(..., description="New status value")
    notes: Optional[str] = Field(None, description="Change reason or notes")
    changed_by: Optional[str] = Field("system", description="Who made the change")


class StatusLogResponse(BaseModel):
    """Response for a single status log entry."""
    id: str
    order_id: str
    from_status: Optional[str]
    to_status: str
    changed_by: Optional[str]
    change_reason: Optional[str]
    changed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TransportOrderResponse(BaseModel):
    """Response for transport order detail."""
    id: str
    application_id: Optional[str]
    order_number: str
    status: str
    current_stage: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    issued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    route_data_json: Optional[Any]
    vehicle_info_json: Optional[Any]
    assessment_json: Optional[Any]
    notes: Optional[str]
    attachments: Optional[Any]
    status_logs: Optional[List[StatusLogResponse]] = None

    class Config:
        from_attributes = True


class TrackingStatistics(BaseModel):
    """Dashboard statistics."""
    total_orders: int = 0
    by_status: dict = Field(default_factory=dict)
    active_orders: int = 0
    completed_today: int = 0
    avg_processing_days: Optional[float] = None
    total_in_transit: int = 0
    approval_rate: Optional[float] = None


class TimelineEntry(BaseModel):
    """Single entry in the order timeline."""
    status: str
    label: str
    timestamp: Optional[datetime]
    is_completed: bool
    is_active: bool
    notes: Optional[str] = None
    changed_by: Optional[str] = None


class OrderDetailResponse(TransportOrderResponse):
    """Extended order detail with timeline."""
    timeline: List[TimelineEntry] = Field(default_factory=list)
