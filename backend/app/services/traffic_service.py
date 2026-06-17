"""
Traffic Condition Service.

Extracts and analyzes traffic data from EXISTING Amap API route responses.
NO new API calls — uses traffic_condition field already in route data.
"""
import re
import logging

logger = logging.getLogger(__name__)


class TrafficService:
    """Traffic condition analysis from Amap route data."""

    @staticmethod
    def analyze_traffic(route_data: dict) -> dict:
        """Analyze traffic conditions from route data.

        Args:
            route_data: Route dict with traffic_condition, steps, distance

        Returns:
            {
                "overall_condition": str,
                "congestion_segments": [...],
                "total_delay_minutes": int,
                "recommended_departure": str,
            }
        """
        condition = route_data.get("traffic_condition", "")
        steps = route_data.get("steps", [])
        distance = route_data.get("distance", 0) / 1000  # km

        # Parse overall condition (format: "畅通 99%" or "缓行 30%, 拥堵 10%")
        congestion_segments = []
        total_delay = 0

        # Analyze per-step traffic from TMC data in steps
        if steps:
            for step in steps:
                tmc_status = step.get("tmc_status", "")
                if not tmc_status:
                    continue
                road_name = step.get("road", "")
                # TMC status: 畅通/缓行/拥堵/严重拥堵
                if "缓行" in tmc_status or "拥堵" in tmc_status:
                    step_distance = step.get("distance", 0) / 1000
                    delay = 0
                    if "缓行" in tmc_status:
                        delay = int(step_distance * 1.5)  # ~1.5 min extra per km
                    elif "拥堵" in tmc_status:
                        delay = int(step_distance * 3)  # ~3 min extra per km
                    elif "严重拥堵" in tmc_status:
                        delay = int(step_distance * 5)

                    congestion_segments.append({
                        "road": road_name or "未知路段",
                        "condition": tmc_status,
                        "distance_km": round(step_distance, 1),
                        "delay_minutes": delay,
                    })
                    total_delay += delay

        # Parse overall from traffic_condition string
        overall = condition or "未知"
        if not congestion_segments and condition:
            # Try to parse percentage
            m = re.search(r'畅通\s*(\d+)%', condition)
            if m and int(m.group(1)) >= 90:
                overall = "畅通"
            elif "缓行" in condition or "拥堵" in condition:
                overall = "部分拥堵"

        # Recommend departure time
        departure_recommendation = "当前路况良好，随时可出发"
        now_hour = 9  # default morning
        try:
            from datetime import datetime
            now_hour = datetime.now().hour
        except (ValueError, TypeError, OSError):
            logger.debug("Could not determine current hour, using default")

        if total_delay > 30:
            departure_recommendation = "建议避开高峰时段（7:00-9:00, 17:00-19:00）出发"
        elif total_delay > 10:
            departure_recommendation = "建议早上6:00前出发以避开早高峰"

        return {
            "overall_condition": overall,
            "congestion_segments": congestion_segments[:10],
            "total_delay_minutes": total_delay,
            "recommended_departure": departure_recommendation,
        }

    @staticmethod
    def format_for_llm(traffic_result: dict) -> str:
        """Format traffic data for LLM context."""
        if not traffic_result:
            return ""
        lines = [
            "【实时路况分析】",
            f"整体路况: {traffic_result.get('overall_condition', '未知')}",
        ]
        segs = traffic_result.get("congestion_segments", [])
        if segs:
            lines.append(f"拥堵路段: {len(segs)}处, 预计延误{traffic_result.get('total_delay_minutes', 0)}分钟")
            for s in segs[:5]:
                lines.append(f"  • {s['road']}: {s['condition']} ({s['distance_km']}km, +{s['delay_minutes']}min)")
        else:
            lines.append("无明显拥堵路段")
        if traffic_result.get("recommended_departure"):
            lines.append(traffic_result["recommended_departure"])
        return "\n".join(lines)


traffic_service = TrafficService()
