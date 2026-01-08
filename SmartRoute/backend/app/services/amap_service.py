
import httpx
from typing import Optional, Tuple, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AmapService:
    BASE_URL = "https://restapi.amap.com"

    @staticmethod
    async def get_geo_code(address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to coordinates using Amap Geocoding API v3.
        """
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
                    logger.warning(f"Geocode failed for '{address}': {data.get('info')}")
        except Exception as e:
            logger.error(f"Geocode exception: {e}")
            
        return None

    @staticmethod
    async def plan_route_driving(
        origin: str, 
        destination: str, 
        strategy: int = 0
    ) -> Dict[str, Any]:
        """
        Plan driving route using Amap Direction API v3.
        origin/destination: "lon,lat"
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
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                return response.json()
        except Exception as e:
            logger.error(f"Route plan exception: {e}")
            return {"status": "0", "info": str(e)}
