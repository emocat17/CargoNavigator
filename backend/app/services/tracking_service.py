"""
Tracking service - core business logic for transport order lifecycle.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.tracking_models import (
    TransportOrder,
    StatusLog,
    VALID_TRANSITIONS,
    STAGE_LABELS,
    VALID_STATUSES,
    generate_uuid,
)

logger = logging.getLogger(__name__)

# Stage ordering for timeline display
STAGE_ORDER = [
    "DRAFT", "SUBMITTED", "UNDER_REVIEW", "FIELD_SURVEY",
    "APPROVED", "PERMIT_ISSUED", "IN_TRANSIT", "COMPLETED"
]
TERMINAL_STAGES = {"COMPLETED", "CANCELLED", "REJECTED"}


class TrackingService:

    # ── Order CRUD ──

    @staticmethod
    def create_order(
        db: Session,
        application_id: Optional[str] = None,
        route_data: Optional[dict] = None,
        vehicle_info: Optional[dict] = None,
        assessment_data: Optional[dict] = None,
        notes: Optional[str] = None,
        attachments: Optional[list] = None,
    ) -> TransportOrder:
        """Create a new transport order and its initial status log."""
        order_number = TrackingService._generate_order_number(db)

        order = TransportOrder(
            application_id=application_id,
            order_number=order_number,
            status="DRAFT",
            current_stage="DRAFT",
            route_data_json=route_data or {},
            vehicle_info_json=vehicle_info or {},
            assessment_json=assessment_data or {},
            notes=notes,
            attachments=attachments or [],
        )
        db.add(order)
        db.flush()

        # Create initial status log
        log = StatusLog(
            order_id=order.id,
            from_status=None,
            to_status="DRAFT",
            changed_by="system",
            change_reason="Order created",
        )
        db.add(log)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def get_order(db: Session, order_id: str) -> Optional[TransportOrder]:
        """Get a single order by ID."""
        return db.query(TransportOrder).filter(TransportOrder.id == order_id).first()

    @staticmethod
    def get_order_by_number(db: Session, order_number: str) -> Optional[TransportOrder]:
        """Get a single order by order number."""
        return db.query(TransportOrder).filter(TransportOrder.order_number == order_number).first()

    @staticmethod
    def get_orders(
        db: Session,
        status: Optional[str] = None,
        application_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> List[TransportOrder]:
        """List orders with optional filters and sorting."""
        q = db.query(TransportOrder)

        if status:
            q = q.filter(TransportOrder.status == status)
        if application_id:
            q = q.filter(TransportOrder.application_id == application_id)

        # Sort
        sort_col = getattr(TransportOrder, sort_by, TransportOrder.created_at)
        if sort_desc:
            q = q.order_by(sort_col.desc())
        else:
            q = q.order_by(sort_col.asc())

        return q.offset(skip).limit(limit).all()

    @staticmethod
    def get_active_orders(db: Session) -> List[TransportOrder]:
        """Get all non-terminal orders (in progress)."""
        return (
            db.query(TransportOrder)
            .filter(TransportOrder.status.notin_(TERMINAL_STAGES))
            .order_by(TransportOrder.updated_at.desc())
            .all()
        )

    @staticmethod
    def update_status(
        db: Session,
        order_id: str,
        new_status: str,
        notes: str = "",
        changed_by: str = "system",
    ) -> Optional[TransportOrder]:
        """Update order status with state-machine validation and timestamps.

        Returns the StatusLog entry, or None if the order is not found.
        Raises ValueError for invalid transitions.
        """
        order = db.query(TransportOrder).filter(TransportOrder.id == order_id).first()
        if not order:
            return None

        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        if new_status not in VALID_TRANSITIONS.get(order.status, []):
            raise ValueError(
                f"Invalid transition: {order.status} -> {new_status}. "
                f"Valid transitions from {order.status}: {VALID_TRANSITIONS.get(order.status, [])}"
            )

        from_status = order.status

        # Create status log
        log = StatusLog(
            order_id=order.id,
            from_status=from_status,
            to_status=new_status,
            changed_by=changed_by,
            change_reason=notes,
        )
        db.add(log)

        # Update order
        order.status = new_status
        order.current_stage = new_status
        now = datetime.utcnow()

        # Set timestamps based on status
        if new_status == "SUBMITTED":
            order.submitted_at = now
        elif new_status == "APPROVED":
            order.approved_at = now
        elif new_status == "PERMIT_ISSUED":
            order.issued_at = now
        elif new_status == "IN_TRANSIT":
            order.started_at = now
        elif new_status == "COMPLETED":
            order.completed_at = now

        db.commit()
        db.refresh(log)
        return log

    # ── Timeline ──

    @staticmethod
    def get_timeline(db: Session, order_id: str) -> List[dict]:
        """Build an enriched timeline for an order.

        Combines the status logs with the defined stage order to produce
        a full timeline showing all stages (completed, active, pending).
        """
        order = db.query(TransportOrder).filter(TransportOrder.id == order_id).first()
        if not order:
            return []

        logs = {
            log.to_status: log
            for log in order.status_logs
        }

        timeline = []

        for stage in STAGE_ORDER:
            log_entry = logs.get(stage)
            is_current = (stage == order.status)

            entry = {
                "status": stage,
                "label": STAGE_LABELS.get(stage, stage),
                "timestamp": log_entry.changed_at.isoformat() if log_entry and log_entry.changed_at else None,
                "is_completed": bool(log_entry and not is_current),
                "is_active": is_current,
                "notes": log_entry.change_reason if log_entry else None,
                "changed_by": log_entry.changed_by if log_entry else None,
            }
            timeline.append(entry)

        # Handle CANCELLED/REJECTED specially if present
        if order.status in ("CANCELLED", "REJECTED"):
            log_entry = logs.get(order.status)
            if log_entry:
                entry = {
                    "status": order.status,
                    "label": STAGE_LABELS.get(order.status, order.status),
                    "timestamp": log_entry.changed_at.isoformat() if log_entry.changed_at else None,
                    "is_completed": False,
                    "is_active": True,
                    "notes": log_entry.change_reason,
                    "changed_by": log_entry.changed_by,
                }
                timeline.append(entry)

        return timeline

    # ── Statistics ──

    @staticmethod
    def get_statistics(db: Session) -> dict:
        """Compute dashboard statistics."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total = db.query(func.count(TransportOrder.id)).scalar() or 0

        # Counts by status
        status_rows = (
            db.query(TransportOrder.status, func.count(TransportOrder.id))
            .group_by(TransportOrder.status)
            .all()
        )
        by_status = {row[0]: row[1] for row in status_rows}

        # Active (non-terminal)
        active = sum(
            count for status, count in by_status.items()
            if status not in TERMINAL_STAGES
        )

        # Completed today
        completed_today = (
            db.query(func.count(TransportOrder.id))
            .filter(
                TransportOrder.status == "COMPLETED",
                TransportOrder.completed_at >= today_start,
            )
            .scalar()
        ) or 0

        # In transit
        in_transit = by_status.get("IN_TRANSIT", 0)

        # Approval rate
        approved = by_status.get("APPROVED", 0)
        rejected = by_status.get("REJECTED", 0)
        decided = approved + rejected
        approval_rate = round(approved / decided * 100, 1) if decided > 0 else None

        # Avg processing time (submitted -> completed, in days)
        avg_days = None
        completed_orders = (
            db.query(TransportOrder)
            .filter(
                TransportOrder.status == "COMPLETED",
                TransportOrder.submitted_at.isnot(None),
                TransportOrder.completed_at.isnot(None),
            )
            .all()
        )
        if completed_orders:
            total_days = sum(
                (o.completed_at - o.submitted_at).total_seconds()
                for o in completed_orders
            )
            avg_days = round(total_days / len(completed_orders) / 86400, 1)

        return {
            "total_orders": total,
            "by_status": by_status,
            "active_orders": active,
            "completed_today": completed_today,
            "avg_processing_days": avg_days,
            "total_in_transit": in_transit,
            "approval_rate": approval_rate,
        }

    # ── Helpers ──

    @staticmethod
    def _generate_order_number(db: Session) -> str:
        """Generate a unique order number like YZ-20260616-0001."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        # Count orders created today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count_today = (
            db.query(func.count(TransportOrder.id))
            .filter(TransportOrder.created_at >= today_start)
            .scalar()
        ) or 0
        seq = str(count_today + 1).zfill(4)
        return f"YZ-{date_str}-{seq}"
