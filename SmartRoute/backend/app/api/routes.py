from fastapi import APIRouter, HTTPException
from app.models.schemas import RoutePlanRequest, RoutePlanResponse, RouteInfo, RouteStep
from app.services.amap_service import AmapService
import re

router = APIRouter()

def is_coordinate(text: str) -> bool:
    # Simple regex to check if string is "lon,lat"
    return bool(re.match(r"^\d+(\.\d+)?,\d+(\.\d+)?$", text))

@router.post("/routes/plan", response_model=RoutePlanResponse)
async def plan_route(request: RoutePlanRequest):
    origin = request.origin
    destination = request.destination
    
    # 1. Geocoding if needed
    if not is_coordinate(origin):
        coords = await AmapService.get_geo_code(origin)
        if not coords:
            raise HTTPException(status_code=400, detail=f"无法解析起点地址: {origin}")
        origin = f"{coords[0]},{coords[1]}"
        
    if not is_coordinate(destination):
        coords = await AmapService.get_geo_code(destination)
        if not coords:
            raise HTTPException(status_code=400, detail=f"无法解析终点地址: {destination}")
        destination = f"{coords[0]},{coords[1]}"
        
    # 2. Call Amap API
    amap_res = await AmapService.plan_route_driving(origin, destination, request.strategy)
    
    if amap_res.get("status") != "1":
        raise HTTPException(status_code=500, detail=f"高德API调用失败: {amap_res.get('info')}")
        
    # 3. Parse Response
    routes = []
    route_data = amap_res.get("route", {})
    paths = route_data.get("paths", [])
    
    for idx, path in enumerate(paths):
        steps = []
        full_polyline = []
        
        for step in path.get("steps", []):
            polyline = step.get("polyline", "")
            steps.append(RouteStep(
                instruction=step.get("instruction", ""),
                distance=int(step.get("distance", 0)),
                duration=int(step.get("duration", 0)),
                polyline=polyline
            ))
            full_polyline.append(polyline)
            
        path_points_str = ";".join(full_polyline)
            
        routes.append(RouteInfo(
            id=str(idx + 1),
            distance=int(path.get("distance", 0)),
            duration=int(path.get("duration", 0)),
            path_points=path_points_str,
            steps=steps
        ))
        
    return RoutePlanResponse(data={"routes": routes})
