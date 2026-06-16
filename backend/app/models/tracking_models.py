"""
Tracking models for whole-process transport status management.
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


# Valid statuses for transport orders
VALID_STATUSES = [
    "DRAFT",           # 草稿
    "SUBMITTED",       # 申请提交
    "UNDER_REVIEW",    # 受理审核
    "FIELD_SURVEY",    # 现场勘验
    "APPROVED",        # 审批决定-通过
    "REJECTED",        # 审批决定-驳回
    "PERMIT_ISSUED",   # 发证
    "IN_TRANSIT",      # 运输中
    "COMPLETED",       # 到达完成
    "CANCELLED",       # 已取消
]

# Valid state transitions
VALID_TRANSITIONS = {
    "DRAFT": ["SUBMITTED", "CANCELLED"],
    "SUBMITTED": ["UNDER_REVIEW", "CANCELLED"],
    "UNDER_REVIEW": ["FIELD_SURVEY", "APPROVED", "REJECTED", "CANCELLED"],
    "FIELD_SURVEY": ["UNDER_REVIEW", "APPROVED", "REJECTED", "CANCELLED"],
    "APPROVED": ["PERMIT_ISSUED", "CANCELLED"],
    "REJECTED": ["SUBMITTED", "CANCELLED"],
    "PERMIT_ISSUED": ["IN_TRANSIT", "CANCELLED"],
    "IN_TRANSIT": ["COMPLETED", "CANCELLED"],
    "COMPLETED": ["CANCELLED"],
    "CANCELLED": ["DRAFT"],
}

# Stage display names
STAGE_LABELS = {
    "DRAFT": "草稿",
    "SUBMITTED": "申请提交",
    "UNDER_REVIEW": "受理审核",
    "FIELD_SURVEY": "现场勘验",
    "APPROVED": "审批通过",
    "REJECTED": "审批驳回",
    "PERMIT_ISSUED": "已发证",
    "IN_TRANSIT": "运输中",
    "COMPLETED": "到达完成",
    "CANCELLED": "已取消",
}


class TransportOrder(Base):
    """Main transport order tracking record."""
    __tablename__ = "transport_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True, index=True)
    order_number = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="DRAFT", nullable=False, index=True)
    current_stage = Column(String, default="DRAFT", nullable=False)

    # Key timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Data payloads (JSON)
    route_data_json = Column(JSON, nullable=True, default=dict)
    vehicle_info_json = Column(JSON, nullable=True, default=dict)
    assessment_json = Column(JSON, nullable=True, default=dict)

    # Metadata
    notes = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True, default=list)

    # Relationships
    status_logs = relationship(
        "StatusLog",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="StatusLog.changed_at",
    )


class StatusLog(Base):
    """Audit log for each status transition."""
    __tablename__ = "status_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("transport_orders.id"), nullable=False, index=True)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    changed_by = Column(String, nullable=True, default="system")
    change_reason = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    order = relationship("TransportOrder", back_populates="status_logs")
