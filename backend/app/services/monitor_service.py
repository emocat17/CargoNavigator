"""
Monitor Service — manages transport monitoring sessions and SSE event streams.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Optional

from sqlalchemy.orm import Session

from app.services.gps_simulator import GPSSimulator

logger = logging.getLogger(__name__)

TZ_UTC8 = timezone(timedelta(hours=8))


def _now_utc8() -> datetime:
    return datetime.now(TZ_UTC8)


class MonitorService:
    """Singleton managing active monitoring sessions."""

    active_sessions: dict[str, dict] = {}

    @classmethod
    async def start_monitoring(cls, order_id: str, db: Session) -> dict:
        if order_id in cls.active_sessions:
            raise ValueError(f"订单 {order_id} 已有活跃监控会话")

        from app.models.tracking_models import TransportOrder
        from app.services.tracking_service import TrackingService

        order = db.query(TransportOrder).filter(TransportOrder.id == order_id).first()
        if not order:
            raise ValueError(f"订单 {order_id} 不存在")

        if order.status != "PERMIT_ISSUED":
            raise ValueError(f"只能对已发证的订单启动监控，当前状态: {order.status}")

        route_data = order.route_data_json or {}
        path_points = route_data.get("path_points", "")
        if not path_points:
            raise ValueError("该订单无路线polyline数据")

        checkpoints = cls._extract_checkpoints(order)
        speed = float(route_data.get("_speed", 60)) if "_speed" in route_data else 60.0
        simulator = GPSSimulator(path_points, checkpoints, speed_kmh=speed)

        TrackingService.update_status(
            db=db, order_id=order_id, new_status="IN_TRANSIT",
            notes="监控已启动", changed_by="monitor_service"
        )

        session = {
            "simulator": simulator,
            "buffer": {"gps": [], "checkpoints": [], "alerts": []},
            "started_at": _now_utc8(),
            "order_id": order_id,
        }
        cls.active_sessions[order_id] = session
        logger.info(f"Monitoring started for order {order_id}")
        return session

    @classmethod
    async def stream_events(cls, order_id: str) -> AsyncGenerator[str, None]:
        if order_id not in cls.active_sessions:
            yield cls._sse("error", json.dumps({"message": "无活跃监控会话"}))
            yield cls._sse("done", "")
            return

        session = cls.active_sessions[order_id]
        simulator = session["simulator"]
        buffer = session["buffer"]

        yield cls._sse("status", json.dumps({
            "status": "monitoring",
            "message": "监控已启动",
            "started_at": session["started_at"].isoformat(),
        }, ensure_ascii=False))

        try:
            async for event in simulator.run():
                yield cls._sse(event["type"], json.dumps(event, ensure_ascii=False))
                if event["type"] == "gps":
                    buffer["gps"].append(event)
                elif event["type"] == "checkpoint":
                    buffer["checkpoints"].append(event)
                elif event["type"] == "alert":
                    buffer["alerts"].append(event)
        except Exception as e:
            logger.error(f"Simulation error for {order_id}: {e}")
            yield cls._sse("alert", json.dumps({
                "alert_type": "system",
                "message": f"模拟异常: {str(e)}",
                "severity": "critical",
                "timestamp": _now_utc8().isoformat(),
            }, ensure_ascii=False))

        yield cls._sse("done", "")

    @classmethod
    async def stop_monitoring(cls, order_id: str, db: Session) -> dict:
        if order_id not in cls.active_sessions:
            raise ValueError(f"订单 {order_id} 无活跃监控会话")

        session = cls.active_sessions.pop(order_id)
        buffer = session["buffer"]

        from app.models.tracking_models import GPSTrackPoint, CheckpointRecord, AlertEvent
        from app.services.tracking_service import TrackingService

        gps_count = 0
        for pt in buffer["gps"]:
            db.add(GPSTrackPoint(
                order_id=order_id,
                longitude=str(pt.get("lon", "")),
                latitude=str(pt.get("lat", "")),
                speed=str(pt.get("speed", 0)),
                heading=str(pt.get("heading", 0)),
                is_simulated="true",
            ))
            gps_count += 1

        cp_count = 0
        for cp in buffer["checkpoints"]:
            db.add(CheckpointRecord(
                order_id=order_id,
                station=cp.get("station", ""),
                checkpoint_type=cp.get("checkpoint_type", cp.get("type", "unknown")),
                highway=cp.get("highway", ""),
                longitude=str(cp.get("lon", "")),
                latitude=str(cp.get("lat", "")),
                actual_pass_time=_now_utc8(),
                notes="模拟通行",
            ))
            cp_count += 1

        alert_count = 0
        for al in buffer["alerts"]:
            db.add(AlertEvent(
                order_id=order_id,
                alert_type=al.get("alert_type", "unknown"),
                message=al.get("message", ""),
                severity=al.get("severity", "medium"),
                longitude=str(al.get("longitude", "")),
                latitude=str(al.get("latitude", "")),
                resolved="false",
            ))
            alert_count += 1

        db.commit()

        TrackingService.update_status(
            db=db, order_id=order_id, new_status="COMPLETED",
            notes="监控已停止，数据已归档", changed_by="monitor_service"
        )

        logger.info(f"Monitoring stopped for {order_id}: {gps_count} GPS, {cp_count} CP, {alert_count} alerts")
        return {
            "order_id": order_id,
            "gps_points_saved": gps_count,
            "checkpoints_saved": cp_count,
            "alerts_saved": alert_count,
            "started_at": session["started_at"].isoformat(),
            "stopped_at": _now_utc8().isoformat(),
        }

    @classmethod
    def get_active_sessions(cls) -> list[dict]:
        return [{"order_id": oid, "started_at": s["started_at"].isoformat()}
                for oid, s in cls.active_sessions.items()]

    @staticmethod
    def _sse(event: str, data: str) -> str:
        return f"event: {event}\ndata: {data}\n\n"

    @staticmethod
    def _extract_checkpoints(order) -> list[dict]:
        checkpoints = []
        assessment = order.assessment_json or {}
        bridge_details = assessment.get("bridge_details", [])
        for b in bridge_details:
            if b.get("station"):
                checkpoints.append({
                    "station": b["station"],
                    "type": "bridge",
                    "highway": b.get("highway", ""),
                    "lon": b.get("longitude") or b.get("lon"),
                    "lat": b.get("latitude") or b.get("lat"),
                })
        return checkpoints


monitor_service = MonitorService()
