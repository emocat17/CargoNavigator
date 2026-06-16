"""
Archive Service — aggregates transport data into digital archives with JSON/PDF export.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.tracking_models import (
    TransportOrder, GPSTrackPoint, CheckpointRecord, AlertEvent,
)
from app.services.tracking_service import TrackingService

logger = logging.getLogger(__name__)

TZ_UTC8 = timezone(timedelta(hours=8))


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


class ArchiveService:

    @staticmethod
    def generate_archive(order_id: str, db: Session) -> dict:
        order = db.query(TransportOrder).filter(TransportOrder.id == order_id).first()
        if not order:
            raise ValueError(f"订单 {order_id} 不存在")

        gps_points = (
            db.query(GPSTrackPoint)
            .filter(GPSTrackPoint.order_id == order_id)
            .order_by(GPSTrackPoint.timestamp.asc())
            .all()
        )
        speeds = [float(p.speed) for p in gps_points if p.speed and _is_float(p.speed)]
        gps_summary = {
            "total_points": len(gps_points),
            "avg_speed": round(sum(speeds) / len(speeds), 1) if speeds else 0,
            "max_speed": round(max(speeds), 1) if speeds else 0,
            "duration_minutes": 0,
        }
        if gps_points and len(gps_points) >= 2:
            first_ts = gps_points[0].timestamp
            last_ts = gps_points[-1].timestamp
            if first_ts and last_ts:
                gps_summary["duration_minutes"] = round(
                    (last_ts - first_ts).total_seconds() / 60, 1
                )

        checkpoints = (
            db.query(CheckpointRecord)
            .filter(CheckpointRecord.order_id == order_id)
            .order_by(CheckpointRecord.actual_pass_time.asc())
            .all()
        )

        alerts = (
            db.query(AlertEvent)
            .filter(AlertEvent.order_id == order_id)
            .order_by(AlertEvent.timestamp.asc())
            .all()
        )

        timeline = TrackingService.get_timeline(db=db, order_id=order_id)

        return {
            "archive_generated_at": datetime.now(TZ_UTC8).isoformat(),
            "order_info": {
                "order_number": order.order_number,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "approved_at": order.approved_at.isoformat() if order.approved_at else None,
                "started_at": order.started_at.isoformat() if order.started_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None,
                "route_data": order.route_data_json,
                "vehicle_info": order.vehicle_info_json,
            },
            "gps_summary": gps_summary,
            "gps_track": [
                {
                    "longitude": p.longitude,
                    "latitude": p.latitude,
                    "speed": p.speed,
                    "heading": p.heading,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                }
                for p in gps_points
            ],
            "checkpoints": [
                {
                    "station": c.station,
                    "type": c.checkpoint_type,
                    "highway": c.highway,
                    "passed_at": c.actual_pass_time.isoformat() if c.actual_pass_time else None,
                    "delay_minutes": c.delay_minutes,
                    "notes": c.notes,
                }
                for c in checkpoints
            ],
            "alerts": [
                {
                    "type": a.alert_type,
                    "message": a.message,
                    "severity": a.severity,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "resolved": a.resolved,
                }
                for a in alerts
            ],
            "timeline": timeline,
        }

    @staticmethod
    def export_json(order_id: str, db: Session) -> str:
        archive = ArchiveService.generate_archive(order_id, db)
        return json.dumps(archive, ensure_ascii=False, indent=2)

    @staticmethod
    def export_pdf(order_id: str, db: Session) -> bytes:
        archive = ArchiveService.generate_archive(order_id, db)
        order_info = archive["order_info"]
        gps = archive["gps_summary"]

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from io import BytesIO

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph("大件运输数字档案", styles["Title"]))
            story.append(Spacer(1, 12))
            story.append(Paragraph("基本信息", styles["Heading2"]))

            info_data = [
                ["运输单号", order_info.get("order_number", "-")],
                ["状态", order_info.get("status", "-")],
                ["发车时间", order_info.get("started_at", "-")],
                ["到达时间", order_info.get("completed_at", "-")],
            ]
            t = Table(info_data, colWidths=[120, 380])
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

            story.append(Paragraph("GPS轨迹摘要", styles["Heading2"]))
            gps_data = [
                ["总记录点数", str(gps.get("total_points", 0))],
                ["平均速度", f"{gps.get('avg_speed', 0)} km/h"],
                ["最高速度", f"{gps.get('max_speed', 0)} km/h"],
                ["行驶时长", f"{gps.get('duration_minutes', 0)} 分钟"],
            ]
            t2 = Table(gps_data, colWidths=[120, 380])
            t2.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ]))
            story.append(t2)

            doc.build(story)
            buffer.seek(0)
            return buffer.read()

        except ImportError:
            text = ArchiveService._text_report(archive)
            return text.encode("utf-8")

    @staticmethod
    def _text_report(archive: dict) -> str:
        lines = [
            "=" * 50,
            "  大件运输数字档案",
            "=" * 50,
            f"运输单号: {archive['order_info'].get('order_number', '-')}",
            f"生成时间: {archive['archive_generated_at']}",
            "",
            f"GPS轨迹: {archive['gps_summary'].get('total_points', 0)}点",
            f"检查点: {len(archive.get('checkpoints', []))}处",
            f"异常事件: {len(archive.get('alerts', []))}个",
        ]
        return "\n".join(lines)


archive_service = ArchiveService()
