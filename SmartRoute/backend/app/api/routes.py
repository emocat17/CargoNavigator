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
    try:
        routes = []
        route_data = amap_res.get("route", {})
        paths = route_data.get("paths", [])
        
        for idx, path in enumerate(paths):
            steps = []
            full_polyline = []
            
            # Stats for traffic and roads
            traffic_stats = {"畅通": 0, "缓行": 0, "拥堵": 0, "未知": 0}
            road_stats = {} # road_name: distance
            total_distance = int(path.get("distance", 0))
            
            # New Tracking Lists
            passed_cities_set = [] # Use list to preserve order, check duplication manually
            _toll_details_temp = [] # Temp list for aggregation [{'name': 'G15', 'cost': 10.5}]

            for step in path.get("steps", []):
                polyline = step.get("polyline", "")
                step_distance = int(step.get("distance", 0))
                road_name = step.get("road", "")
                
                # Extract Cities
                cities = step.get("cities", [])
                for city in cities:
                    city_name = city.get("name", "")
                    districts = city.get("districts", [])
                    district_name = districts[0].get("name", "") if districts else ""
                    
                    full_name = f"{city_name}"
                    if district_name:
                        full_name += f"({district_name})"
                    
                    if full_name and (not passed_cities_set or passed_cities_set[-1] != full_name):
                        passed_cities_set.append(full_name)

                # Extract Toll Roads
                toll_road_name = step.get("toll_road", "")
                step_tolls = float(step.get("tolls", 0))
                if toll_road_name and step_tolls > 0:
                     if _toll_details_temp and _toll_details_temp[-1]['name'] == toll_road_name:
                         _toll_details_temp[-1]['cost'] += step_tolls
                     else:
                         _toll_details_temp.append({'name': toll_road_name, 'cost': step_tolls})

                # Handle potential list values for actions
                action = step.get("action", "")
                if isinstance(action, list):
                    action = ";".join([str(a) for a in action])
                    
                assistant_action = step.get("assistant_action", "")
                if isinstance(assistant_action, list):
                    assistant_action = ";".join([str(a) for a in assistant_action])
                
                # Populate new Step fields
                tmcs_data = []
                tmcs_list = step.get("tmcs", [])
                if tmcs_list:
                    for tmc in tmcs_list:
                        try:
                            tmcs_data.append(TMC(
                                distance=int(tmc.get("distance", 0)),
                                status=str(tmc.get("status", "未知")),
                                polyline=str(tmc.get("polyline", ""))
                            ))
                        except Exception as e:
                            print(f"Error parsing TMC: {e}, Data: {tmc}")

                steps.append(RouteStep(
                    instruction=step.get("instruction", ""),
                    distance=step_distance,
                    duration=int(step.get("duration", 0)),
                    polyline=polyline,
                    road=road_name,
                    action=action,
                    assistant_action=assistant_action,
                    tmcs=tmcs_data
                ))
                full_polyline.append(polyline)
                
                # Road Stats
                if road_name:
                    road_stats[road_name] = road_stats.get(road_name, 0) + step_distance
                    
                # Traffic Stats from tmcs
                tmcs = step.get("tmcs", [])
                if tmcs:
                    for tmc in tmcs:
                        status = tmc.get("status", "未知")
                        tmc_dist = int(tmc.get("distance", 0))
                        if status in traffic_stats:
                            traffic_stats[status] += tmc_dist
                        else:
                            traffic_stats["未知"] += tmc_dist
                else:
                    # Fallback if no tmcs, assume unknown for this step
                    traffic_stats["未知"] += step_distance
                
            path_points_str = ";".join(full_polyline)
            
            # Convert Toll Details Temp to List[str]
            toll_roads_details = [f"{item['name']}: ¥{item['cost']:.2f}" for item in _toll_details_temp]

            # Calculate Major Roads (Top 3 by distance)
            sorted_roads = sorted(road_stats.items(), key=lambda x: x[1], reverse=True)
            major_roads = [r[0] for r in sorted_roads[:3]]
            
            # Calculate Traffic Condition Summary
            # e.g. "畅通 80%, 缓行 20%"
            traffic_parts = []
            if total_distance > 0:
                for status in ["畅通", "缓行", "拥堵"]:
                    dist = traffic_stats.get(status, 0)
                    if dist > 0:
                        percent = int((dist / total_distance) * 100)
                        if percent > 0:
                            traffic_parts.append(f"{status} {percent}%")
            
            traffic_condition = ", ".join(traffic_parts) if traffic_parts else "路况未知"
                
            routes.append(RouteInfo(
                id=str(idx + 1),
                distance=total_distance,
                duration=int(path.get("duration", 0)),
                path_points=path_points_str,
                steps=steps,
                toll_distance=int(path.get("toll_distance", 0)),
                toll_cost=float(path.get("tolls", 0)),
                traffic_lights=int(path.get("traffic_lights", 0)),
                strategy=path.get("strategy", ""),
                restriction=int(path.get("restriction", 0)),
                traffic_condition=traffic_condition,
                major_roads=major_roads,
                passed_cities=passed_cities_set,
                toll_roads_details=toll_roads_details
            ))
            
        return RoutePlanResponse(data={"routes": routes})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
