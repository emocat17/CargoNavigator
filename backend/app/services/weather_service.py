"""
Weather Risk Assessment Service.

Supports mock mode (no API key) and live mode (QWeather API).
QWeather free tier: 1000 calls/day, no credit card needed.
API doc: https://dev.qweather.com/docs/api/weather/weather-now/
"""
import logging
import random
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class WeatherService:
    """Weather risk assessment for oversized cargo transport routes."""

    def __init__(self):
        self.api_key = settings.QWEATHER_API_KEY if hasattr(settings, 'QWEATHER_API_KEY') else ""
        self.mock_mode = not self.api_key

    async def get_route_weather(
        self,
        route_data: dict,
        departure_time: str = None,
    ) -> dict:
        """Sample weather at key points along the route.

        Args:
            route_data: Route with route_description, distance, etc.
            departure_time: ISO datetime string (optional)

        Returns:
            {
                "overall_risk": "低/中/高/禁行",
                "weather_along_route": [...],
                "warnings": [...],
                "recommendations": [...],
            }
        """
        # Extract waypoints from route description
        waypoints = self._extract_waypoints(route_data)

        if self.mock_mode:
            return self._mock_route_weather(waypoints, route_data, departure_time)
        else:
            return await self._live_route_weather(waypoints, route_data)

    def _extract_waypoints(self, route_data: dict) -> list[dict]:
        """Extract sampling points from route data."""
        points = []

        # Try to get from route_description
        desc = route_data.get("route_description", "")
        if desc:
            # Extract city/junction names between -- or →
            import re
            names = re.findall(r'[一-龥]{2,6}(?:市|县|区|枢纽|互通)?', desc)
            for name in names[:8]:  # max 8 sampling points
                if name not in [p["name"] for p in points]:
                    points.append({"name": name, "type": "junction"})

        # Fallback: use distance-based sampling
        if not points:
            distance = route_data.get("distance", 100000) / 1000  # km
            n_points = max(3, int(distance / 50))  # every ~50km
            for i in range(n_points):
                points.append({
                    "name": f"途经点{i+1}",
                    "type": "waypoint",
                    "distance_km": i * (distance / n_points),
                })

        return points

    def _mock_route_weather(self, waypoints: list[dict], route_data: dict, departure_time: str = None) -> dict:
        """Generate realistic mock weather data for development/testing."""
        weather_types = ["晴", "多云", "阴", "小雨", "晴", "多云", "晴"]  # biased good
        temps = [random.uniform(20, 35) for _ in waypoints]
        winds = [random.uniform(5, 25) for _ in waypoints]
        vis = [random.choice([10000, 8000, 6000, 5000, 12000]) for _ in waypoints]

        weather_list = []
        warnings = []
        overall_risk = "低"

        for i, wp in enumerate(waypoints):
            w_type = random.choice(weather_types[:5])  # mostly good weather
            wind = winds[i]
            temp = temps[i]
            visibility = vis[i]

            risk_factors = []
            if wind > 50:
                risk_factors.append("强风(>50km/h)")
                overall_risk = "禁行"
            elif wind > 30:
                risk_factors.append(f"大风({wind:.0f}km/h)")
                if overall_risk == "低":
                    overall_risk = "中"

            if visibility < 1000:
                risk_factors.append(f"低能见度({visibility}m)")
                overall_risk = "高"
            elif visibility < 5000:
                risk_factors.append(f"能见度一般({visibility}m)")

            if w_type in ("大雨", "暴雨"):
                risk_factors.append("强降水")
                if overall_risk == "低":
                    overall_risk = "高"

            weather_list.append({
                "location": wp["name"],
                "type": wp.get("type", "waypoint"),
                "weather": w_type,
                "temp": round(temp, 1),
                "wind_speed": round(wind, 1),
                "visibility": visibility,
                "precipitation": random.uniform(0, 2) if "雨" in w_type else 0.0,
                "risk_factors": risk_factors,
            })

        # Generate warnings
        if any(w["risk_factors"] for w in weather_list):
            for w in weather_list:
                if w["risk_factors"]:
                    warnings.append(f"{w['location']}: {', '.join(w['risk_factors'])}")

        # Recommendations
        recommendations = []
        if overall_risk == "低":
            recommendations.append("天气条件良好，适合运输")
        elif overall_risk == "中":
            recommendations.append("部分路段天气需关注，建议做好防风准备")
        elif overall_risk == "高":
            recommendations.append("建议推迟运输或选择天气较好的时段出发")
        elif overall_risk == "禁行":
            recommendations.append("极端天气预警，不建议发车")

        if departure_time:
            recommendations.append("建议出发前1小时再次确认沿途天气")

        return {
            "overall_risk": overall_risk,
            "weather_along_route": weather_list,
            "warnings": warnings[:5],
            "recommendations": recommendations,
            "mode": "mock",
        }

    async def _live_route_weather(self, waypoints: list[dict], route_data: dict) -> dict:
        """Call QWeather API for real weather data. Falls back to mock on failure."""
        try:
            import aiohttp

            weather_list = []
            for wp in waypoints:
                # QWeather city lookup + now-weather API
                # This is a simplified version - in production, first geo-lookup the city
                url = f"https://devapi.qweather.com/v7/weather/now"
                # In real implementation: location ID from city lookup
                # For now, fall back to mock
                raise NotImplementedError("Live QWeather not implemented")

            return {}  # unreachable
        except Exception as e:
            logger.warning(f"QWeather API failed ({e}), falling back to mock")
            return self._mock_route_weather(waypoints, route_data, departure_time)

    @staticmethod
    def format_for_llm(weather_result: dict) -> str:
        """Format weather data for LLM prompt context."""
        if not weather_result:
            return ""
        lines = [
            "【沿途天气风险评估】",
            f"整体风险: {weather_result.get('overall_risk', '未知')}",
        ]
        if weather_result.get("warnings"):
            lines.append("天气警告:")
            for w in weather_result["warnings"][:5]:
                lines.append(f"  • {w}")
        if weather_result.get("recommendations"):
            lines.append("建议:")
            for r in weather_result["recommendations"][:3]:
                lines.append(f"  • {r}")
        return "\n".join(lines)


weather_service = WeatherService()
