
import httpx
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Fallback city coordinates for Fujian province (lon, lat)
# Used when Amap geocoding API is unavailable
CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "三明": (117.636, 26.263),
    "三明市": (117.636, 26.263),
    "福州": (119.296, 26.074),
    "福州市": (119.296, 26.074),
    "平潭": (119.789, 25.508),
    "平潭县": (119.789, 25.508),
    "平潭综合实验区": (119.789, 25.508),
    "厦门": (118.089, 24.480),
    "厦门市": (118.089, 24.480),
    "泉州": (118.676, 24.874),
    "泉州市": (118.676, 24.874),
    "漳州": (117.647, 24.513),
    "漳州市": (117.647, 24.513),
    "莆田": (119.008, 25.454),
    "莆田市": (119.008, 25.454),
    "宁德": (119.548, 26.666),
    "宁德市": (119.548, 26.666),
    "龙岩": (117.017, 25.075),
    "龙岩市": (117.017, 25.075),
    "南平": (118.178, 26.642),
    "南平市": (118.178, 26.642),
}


class AmapService:
    BASE_URL = "https://restapi.amap.com"

    @staticmethod
    async def get_geo_code(address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to coordinates using Amap Geocoding API v3.
        Falls back to hardcoded city coordinates for Fujian province.
        """
        # Try API first
        url = f"{AmapService.BASE_URL}/v3/geocode/geo"
        params = {
            "address": address,
            "key": settings.AMAP_API_KEY,
            "output": "json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()

                if data.get("status") == "1" and int(data.get("count", 0)) > 0:
                    location = data["geocodes"][0]["location"].split(",")
                    return float(location[0]), float(location[1])
                else:
                    logger.warning(f"Geocode API failed for '{address}': {data.get('info')}")
        except Exception as e:
            logger.error(f"Geocode exception: {e}")

        # Fallback: hardcoded city lookup
        clean = address.strip().rstrip("，。,.")
        if clean in CITY_COORDS:
            logger.info(f"Using fallback coords for '{clean}': {CITY_COORDS[clean]}")
            return CITY_COORDS[clean]

        # Try partial match
        for name, coords in CITY_COORDS.items():
            if clean in name or name in clean:
                logger.info(f"Using partial match coords for '{clean}' → '{name}': {coords}")
                return coords

        return None

    @staticmethod
    async def plan_route_driving(
        origin: str, 
        destination: str, 
        strategy: int = 0,
        waypoints: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plan driving route using Amap Direction API v3.
        origin/destination: "lon,lat"
        waypoints: "lon,lat;lon,lat" (Max 16 waypoints)
        """
        url = f"{AmapService.BASE_URL}/v3/direction/driving"
        params = {
            "origin": origin,
            "destination": destination,
            "strategy": strategy,
            "key": settings.AMAP_API_KEY,
            "output": "json",
            "extensions": "all"
        }
        
        if waypoints:
            params["waypoints"] = waypoints
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                return response.json()
        except Exception as e:
            logger.error(f"Route plan exception: {e}")
            return {"status": "0", "info": str(e)}
