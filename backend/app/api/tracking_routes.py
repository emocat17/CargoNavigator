"""
Tracking API Endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tracking_models import TransportOrder
from app.schemas.tracking_schemas import (
    TransportOrderCreate,
    StatusUpdateRequest,
    TransportOrderResponse,
)
from app.services.tracking_service import TrackingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tracking",
    tags=["tracking"],
    responses={404: {"description": "Not found"}},
)


@router.post("/orders", status_code=http_status.HTTP_201_CREATED)
def create_order(payload: TransportOrderCreate, db: Session = Depends(get_db)):
    """Create a new transport order."""
    try:
        order = TrackingService.create_order(
            db=db,
            application_id=payload.application_id,
            route_data=payload.route_data,
            vehicle_info=payload.vehicle_info,
            assessment_data=payload.assessment_data,
            notes=payload.notes,
            attachments=payload.attachments,
        )
        return {"code": 200, "msg": "success", "data": TransportOrderResponse.from_orm(order).model_dump()}
    except Exception as e:
        logger.exception(f"Failed to create order: {e}")
        raise HTTPException(status_code=500, detail=f"创建运输单失败: {str(e)}")


@router.get("/orders")
def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    application_id: Optional[str] = Query(None, description="Filter by application ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    db: Session = Depends(get_db),
):
    """List transport orders with optional filtering and sorting."""
    try:
        orders = TrackingService.get_orders(
            db=db,
            status=status,
            application_id=application_id,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        total = db.query(TransportOrder).count()
        data = [TransportOrderResponse.from_orm(o).model_dump() for o in orders]
        return {"code": 200, "msg": "success", "data": {"orders": data, "total": total, "skip": skip, "limit": limit}}
    except Exception as e:
        logger.exception(f"Failed to list orders: {e}")
        raise HTTPException(status_code=500, detail=f"获取运输单列表失败: {str(e)}")


@router.get("/orders/active")
def list_active_orders(db: Session = Depends(get_db)):
    """List all active (non-terminal) orders."""
    try:
        orders = TrackingService.get_active_orders(db=db)
        data = [TransportOrderResponse.from_orm(o).model_dump() for o in orders]
        return {"code": 200, "msg": "success", "data": {"orders": data, "count": len(data)}}
    except Exception as e:
        logger.exception(f"Failed to list active orders: {e}")
        raise HTTPException(status_code=500, detail=f"获取活跃运输单失败: {str(e)}")


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get an order with its full timeline."""
    try:
        order = TrackingService.get_order(db=db, order_id=order_id)
        if not order:
            raise HTTPException(status_code=404, detail="运输单不存在")

        timeline = TrackingService.get_timeline(db=db, order_id=order_id)
        order_data = TransportOrderResponse.from_orm(order).model_dump()
        order_data["timeline"] = timeline
        return {"code": 200, "msg": "success", "data": order_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取运输单详情失败: {str(e)}")


@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: str,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update an order's status (state machine validated)."""
    try:
        log = TrackingService.update_status(
            db=db,
            order_id=order_id,
            new_status=payload.new_status,
            notes=payload.notes,
            changed_by=payload.changed_by or "system",
        )
        if log is None:
            raise HTTPException(status_code=404, detail="运输单不存在")

        # Return the updated order with timeline
        order = TrackingService.get_order(db=db, order_id=order_id)
        timeline = TrackingService.get_timeline(db=db, order_id=order_id)
        order_data = TransportOrderResponse.from_orm(order).model_dump()
        order_data["timeline"] = timeline
        return {"code": 200, "msg": "success", "data": order_data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update status for {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"更新运输单状态失败: {str(e)}")


@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    """Get dashboard-level statistics."""
    try:
        stats = TrackingService.get_statistics(db=db)
        return {"code": 200, "msg": "success", "data": stats}
    except Exception as e:
        logger.exception(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")
