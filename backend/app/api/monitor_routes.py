"""
Monitor & Archive API Endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.monitor_service import monitor_service
from app.services.archive_service import archive_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Monitor & Archive"])


@router.post("/monitor/start/{order_id}")
async def start_monitoring(
    order_id: str,
    speed: Optional[float] = Query(None, description="模拟速度 km/h"),
    db: Session = Depends(get_db),
):
    try:
        session = await monitor_service.start_monitoring(order_id, db)
        return {
            "code": 200, "msg": "监控已启动",
            "data": {
                "order_id": order_id,
                "started_at": session["started_at"].isoformat(),
                "checkpoints_count": len(session["simulator"].checkpoints),
                "route_distance_km": round(session["simulator"].total_distance_m / 1000, 1),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"启动监控失败: {str(e)}")


@router.get("/monitor/stream/{order_id}")
async def stream_monitor(order_id: str):
    async def event_stream():
        async for frame in monitor_service.stream_events(order_id):
            yield frame

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/monitor/stop/{order_id}")
async def stop_monitoring(order_id: str, db: Session = Depends(get_db)):
    try:
        summary = await monitor_service.stop_monitoring(order_id, db)
        return {"code": 200, "msg": "监控已停止，数据已归档", "data": summary}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"停止监控失败: {str(e)}")


@router.get("/monitor/sessions")
async def list_sessions():
    sessions = monitor_service.get_active_sessions()
    return {"code": 200, "msg": "success", "data": {"sessions": sessions, "count": len(sessions)}}


@router.get("/archive/{order_id}")
async def get_archive(order_id: str, db: Session = Depends(get_db)):
    try:
        data = archive_service.generate_archive(order_id, db)
        return {"code": 200, "msg": "success", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to generate archive: {e}")
        raise HTTPException(status_code=500, detail=f"生成档案失败: {str(e)}")


@router.get("/archive/{order_id}/export")
async def export_archive(
    order_id: str,
    format: str = Query("json", description="json or pdf"),
    db: Session = Depends(get_db),
):
    try:
        if format == "pdf":
            content = archive_service.export_pdf(order_id, db)
            media_type = "application/pdf"
            filename = f"archive_{order_id}.pdf"
        else:
            content = archive_service.export_json(order_id, db)
            media_type = "application/json"
            filename = f"archive_{order_id}.json"

        return Response(
            content=content, media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to export archive: {e}")
        raise HTTPException(status_code=500, detail=f"导出档案失败: {str(e)}")
