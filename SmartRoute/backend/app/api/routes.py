from fastapi import APIRouter, HTTPException
from app.models.schemas import RoutePlanRequest, RoutePlanResponse, RouteInfo, RouteStep, TMC
from app.services.amap_service import AmapService
import re
import asyncio
from datetime import datetime, timedelta

router = APIRouter()

# Constants for Cost Estimation
FUEL_PRICE = 7.8  # CNY/L (Avg Diesel Price)
FUEL_CONSUMPTION_100KM = 35  # L/100km (Heavy Truck)

def calculate_fuel_cost(distance_m: int, traffic_lights: int) -> float:
    """
    Calculate estimated fuel cost based on distance and traffic lights.
    """
    dist_km = distance_m / 1000
    # Base fuel
    fuel_needed = (dist_km / 100) * FUEL_CONSUMPTION_100KM
    # Traffic light penalty (approx 0.3L per stop/start)
    fuel_needed += traffic_lights * 0.3
    
    return round(fuel_needed * FUEL_PRICE, 2)

def check_night_driving(duration_sec: int, start_time: datetime = None) -> bool:
    """
    Check if the trip overlaps with Night Driving hours (02:00 - 05:00).
    """
    if start_time is None:
        start_time = datetime.now()

    end_time = start_time + timedelta(seconds=duration_sec)
    
    # Check simple overlap
    current = start_time
    while current < end_time:
        if 2 <= current.hour < 5:
            return True
        current += timedelta(minutes=30) # Check granularity: 30 mins
    
    # Check end time specifically
    if 2 <= end_time.hour < 5:
        return True
        
    return False

def is_coordinate(text: str) -> bool:
    # Simple regex to check if string is "lon,lat"
    return bool(re.match(r"^\d+(\.\d+)?,\d+(\.\d+)?$", text))

def deduplicate_redundant_points(points: list[str]) -> list[str]:
    """
    Advanced deduplication for route description.
    Handles:
    1. "沿" prefix redundancy.
    2. Repeated road names separated by points (hubs/tolls).
    3. Main Road vs Auxiliary Road redundancy.
    """
    if not points:
        return []
    
    cleaned = []
    last_road = None
    
    # Keywords that identify a "Point" (Node) rather than a "Road" (Edge)
    point_keywords = ["枢纽", "互通", "收费站", "服务区", "立交", "出入口", "出口", "入口"]
    
    for p in points:
        # 1. Clean "沿" prefix for comparison
        core_p = p[1:] if p.startswith("沿") else p
        
        # 2. Basic "沿" Redundancy Check with immediate previous
        if cleaned:
            prev = cleaned[-1]
            prev_core = prev[1:] if prev.startswith("沿") else prev
            
            # If current is just "沿" version of previous or vice versa
            if core_p == prev_core:
                # Prefer the one without "沿" if possible, or just keep previous?
                # User prefers concise: "吉口互通" over "沿吉口互通"
                if p.startswith("沿") and not prev.startswith("沿"):
                    continue # Skip "沿X" if "X" exists
                if not p.startswith("沿") and prev.startswith("沿"):
                    cleaned[-1] = p # Replace "沿X" with "X"
                    # Update last_road if we are replacing the road
                    if not any(kw in p for kw in point_keywords):
                        last_road = p
                    continue
                continue # Exact duplicate
            
            # Containment Check (e.g. "沿G1517...途径..." vs "G1517...")
            # If prev is long "沿...途径..." and contains current (shorter/cleaner)
            if prev.startswith("沿") and core_p in prev:
                 cleaned[-1] = p
                 # Update last_road if we are replacing the road
                 if not any(kw in core_p for kw in point_keywords):
                     last_road = core_p
                 continue
            # If current is long "沿...途径..." and contains prev
            if p.startswith("沿") and prev_core in p:
                 continue

        # 3. Road vs Point Logic
        is_point = any(kw in core_p for kw in point_keywords)
        
        if not is_point:
            # It is treated as a Road (or generic location)
            if last_road:
                # Check for Exact Repetition (e.g. G1517 ... G1517)
                if core_p == last_road:
                    continue
                
                # Check for Auxiliary Road (e.g. XX大道 -> XX大道辅路)
                if "辅路" in core_p and core_p.startswith(last_road):
                    continue
            
            # Update last_road (Only update if it's a road/path)
            last_road = core_p
        
        cleaned.append(p)
            
    return cleaned

def process_route_data(amap_res: dict, strategy_label: str, departure_time: datetime = None, origin_label: str = "起点", destination_label: str = "终点") -> list[RouteInfo]:
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
        
        # Tunnel Stats
        tunnel_count = 0
        tunnel_distance = 0
        
        # Key Points Description Logic
        key_points = [origin_label]
        last_road = ""
        
        # Keywords to extract as points
        point_keywords = ["枢纽", "收费站", "服务区", "互通", "界"]

        for step in path.get("steps", []):
            polyline = step.get("polyline", "")
            step_distance = int(step.get("distance", 0))
            road_name = step.get("road", "")
            instruction = step.get("instruction", "")
            
            # 1. Extract Points from Instructions
            # Logic: If instruction contains keyword, extract the keyword phrase
            # Simplification: Find the keyword and the 2 chars before/after, or use regex
            # Better approach: Check if assistant_action has meaningful content
            assistant_action = step.get("assistant_action", "")
            if isinstance(assistant_action, list):
                assistant_action = ";".join([str(a) for a in assistant_action])
                
            # Check for Key Points in assistant_action or instruction
            current_point = ""
            
            # Helper to find keyword in text
            def find_keyword(text):
                for kw in point_keywords:
                    if kw in text:
                        # Try to extract the full name e.g. "东寨枢纽"
                        # Simple regex: [\u4e00-\u9fa5A-Za-z0-9]+kw
                        match = re.search(r'([\u4e00-\u9fa5A-Za-z0-9]+' + kw + ')', text)
                        if match:
                            return match.group(1)
                return None

            # Priority 1: Assistant Action (usually "到达XX枢纽")
            extracted = find_keyword(assistant_action)
            if not extracted:
                # Priority 2: Instruction (usually "从XX枢纽出口离开")
                extracted = find_keyword(instruction)
            
            if extracted:
                # Avoid duplicates (e.g. adjacent steps mentioning same hub)
                if key_points[-1] != extracted:
                     key_points.append(extracted)
            
            # 2. Extract Road Names
            if road_name and road_name != last_road:
                # Add road if it's not the same as the last added item (which might be a point or road)
                # Filter out Tunnels from description
                if "隧道" not in road_name and key_points[-1] != road_name:
                    key_points.append(road_name)
                last_road = road_name
            
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
                
            # assistant_action already processed above
            
            # Check for Tunnel
            # Heuristic: "隧道" in road name OR assistant_action contains "进入隧道" OR instruction contains "隧道"
            is_tunnel = "隧道" in road_name or "隧道" in assistant_action or "隧道" in instruction
            if is_tunnel:
                tunnel_count += 1
                tunnel_distance += step_distance

            # Populate new Step fields
            tmcs_data = []
            tmcs_list = step.get("tmcs", [])
            step_traffic_status = "未知"
            
            # Determine Step Traffic Status (Worst case)
            has_congestion = False
            has_slow = False
            has_clear = False

            if tmcs_list:
                for tmc in tmcs_list:
                    status = str(tmc.get("status", "未知"))
                    tmc_dist = int(tmc.get("distance", 0))
                    
                    # Update Global Stats
                    if status in traffic_stats:
                        traffic_stats[status] += tmc_dist
                    else:
                        traffic_stats["未知"] += tmc_dist
                        
                    # Update Step Status Flags
                    if status == "拥堵":
                        has_congestion = True
                    elif status == "缓行":
                        has_slow = True
                    elif status == "畅通":
                        has_clear = True
                        
                    try:
                        tmcs_data.append(TMC(
                            distance=tmc_dist,
                            status=status,
                            polyline=str(tmc.get("polyline", ""))
                        ))
                    except Exception as e:
                        print(f"Error parsing TMC: {e}, Data: {tmc}")
            else:
                # Fallback if no tmcs
                traffic_stats["未知"] += step_distance
            
            if has_congestion:
                step_traffic_status = "拥堵"
            elif has_slow:
                step_traffic_status = "缓行"
            elif has_clear:
                step_traffic_status = "畅通"

            steps.append(RouteStep(
                instruction=instruction,
                distance=step_distance,
                duration=int(step.get("duration", 0)),
                polyline=polyline,
                road=road_name,
                action=action,
                assistant_action=assistant_action,
                tmcs=tmcs_data,
                traffic_status=step_traffic_status
            ))
            full_polyline.append(polyline)
            
            # Road Stats
            if road_name:
                road_stats[road_name] = road_stats.get(road_name, 0) + step_distance
            
        path_points_str = ";".join(full_polyline)
        
        # Global City Deduplication (Unique Values + Specificity Upgrade)
        cleaned_cities = []
        for city in passed_cities_set:
            base = city.split('(')[0]
            should_add = True
            
            # Check against existing result to ensure uniqueness and handle upgrades
            for i, existing in enumerate(cleaned_cities):
                existing_base = existing.split('(')[0]
                
                # 1. Exact Match -> Ignore
                if existing == city:
                    should_add = False
                    break
                
                # 2. Same Base Logic
                if existing_base == base:
                    current_has_district = '(' in city
                    existing_has_district = '(' in existing
                    
                    if current_has_district and not existing_has_district:
                        # Upgrade Generic to Specific (e.g. Sanming -> Sanming(Youxi))
                        cleaned_cities[i] = city
                        should_add = False
                        break
                        
                    elif not current_has_district and existing_has_district:
                        # Ignore Generic if Specific exists (e.g. Sanming(Youxi) -> Sanming)
                        should_add = False
                        break
            
            if should_add:
                cleaned_cities.append(city)
        passed_cities_set = cleaned_cities
        
        # Convert Toll Details Temp to List[str]
        toll_roads_details = [f"{item['name']}: ¥{item['cost']:.2f}" for item in _toll_details_temp]

        # Calculate Major Roads (Top 3 by distance)
        sorted_roads = sorted(road_stats.items(), key=lambda x: x[1], reverse=True)
        major_roads = [r[0] for r in sorted_roads[:3]]
        
        # Calculate Traffic Condition Summary
        traffic_parts = []
        if total_distance > 0:
            for status in ["畅通", "缓行", "拥堵"]:
                dist = traffic_stats.get(status, 0)
                if dist > 0:
                    percent = int((dist / total_distance) * 100)
                    if percent > 0:
                        traffic_parts.append(f"{status} {percent}%")
        
        traffic_condition = ", ".join(traffic_parts) if traffic_parts else "路况未知"
        
        # Calculate P2 Metrics (Cost & Tags)
        est_fuel = calculate_fuel_cost(total_distance, int(path.get("traffic_lights", 0)))
        total_tolls = float(path.get("tolls", 0))
        total_cost_val = est_fuel + total_tolls
        
        route_tags = [strategy_label]
        if check_night_driving(int(path.get("duration", 0)), departure_time):
            route_tags.append("夜间行车")
            
        # Finalize Key Points
        if key_points[-1] != destination_label:
            key_points.append(destination_label)
        
        # Deduplicate redundant points
        key_points = deduplicate_redundant_points(key_points)
        
        route_description = "--".join(key_points)

        routes.append(RouteInfo(
            id=str(idx + 1), # ID will be regenerated later
            distance=total_distance,
            duration=int(path.get("duration", 0)),
            path_points=path_points_str,
            steps=steps,
            toll_distance=int(path.get("toll_distance", 0)),
            toll_cost=float(path.get("tolls", 0)),
            traffic_lights=int(path.get("traffic_lights", 0)),
            strategy=path.get("strategy", strategy_label),
            restriction=int(path.get("restriction", 0)),
            traffic_condition=traffic_condition,
            major_roads=major_roads,
            passed_cities=passed_cities_set,
            toll_roads_details=toll_roads_details,
            tunnel_count=tunnel_count,
            tunnel_distance=tunnel_distance,
            estimated_fuel_cost=est_fuel,
            total_cost=total_cost_val,
            tags=route_tags,
            route_description=route_description
        ))
    return routes

@router.post("/routes/plan", response_model=RoutePlanResponse)
async def plan_route(request: RoutePlanRequest):
    # Preserve original labels for description
    origin_label = request.origin
    destination_label = request.destination

    origin = request.origin
    destination = request.destination
    
    # 1. Geocoding if needed
    if not is_coordinate(origin):
        coords = await AmapService.get_geo_code(origin)
        if not coords:
            raise HTTPException(status_code=400, detail=f"无法解析起点地址: {origin}")
        origin = f"{coords[0]},{coords[1]}"
    else:
        # If input is coordinate, keep it as label or try to use generic name?
        # User requested "Replace with user input". If user input is coord, we use coord.
        pass 
        
    if not is_coordinate(destination):
        coords = await AmapService.get_geo_code(destination)
        if not coords:
            raise HTTPException(status_code=400, detail=f"无法解析终点地址: {destination}")
        destination = f"{coords[0]},{coords[1]}"
    else:
        pass
    
    # Parse Departure Time
    dep_time = None
    target_count = request.route_count

    if request.departure_time:
        try:
            dep_time = datetime.fromisoformat(request.departure_time)
        except:
            pass

    # 2. Call Amap API Concurrently (Multi-Strategy)
    # Strategies: 0(Speed), 1(Cost), 2(Distance), 9(Congestion)
    strategy_map = {
        0: "速度优先",
        1: "费用优先",
        2: "距离优先",
        9: "躲避拥堵"
    }
    strategies = [0, 1, 2, 9]
    
    tasks = [AmapService.plan_route_driving(origin, destination, s) for s in strategies]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_routes = []
    
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"Strategy {strategies[i]} failed: {res}")
            continue
            
        if isinstance(res, dict) and res.get("status") == "1":
            strategy_label = strategy_map.get(strategies[i], "未知策略")
            try:
                processed_routes = process_route_data(
                    res, 
                    strategy_label, 
                    dep_time,
                    origin_label=origin_label,
                    destination_label=destination_label
                )
                all_routes.extend(processed_routes)
            except Exception as e:
                print(f"Error processing strategy {strategies[i]}: {e}")
    
    if not all_routes:
        raise HTTPException(status_code=500, detail="所有策略规划均失败，请检查起终点或网络")

    # 3. Deduplicate Routes
    # Key: distance + duration + toll_cost + traffic_lights
    unique_routes = []
    seen_keys = set()
    
    for r in all_routes:
        key = f"{r.distance}_{r.duration}_{r.toll_cost}_{r.traffic_lights}"
        if key not in seen_keys:
            seen_keys.add(key)
            # Assign unique ID
            r.id = str(len(unique_routes) + 1)
            unique_routes.append(r)
        else:
            # Merge tags (e.g. "Speed" & "Congestion" might be same route)
            # Find the existing route
            existing = next((ex for ex in unique_routes if f"{ex.distance}_{ex.duration}_{ex.toll_cost}_{ex.traffic_lights}" == key), None)
            if existing:
                # Add tag if not present
                new_tag = r.tags[0] # The strategy tag is usually the first one
                if new_tag not in existing.tags:
                    existing.tags.insert(0, new_tag) # Insert at start
                    # Update strategy string to reflect multi-strategy
                    existing.strategy += f"/{r.strategy}"
    
    # Limit to requested count
    # Sort by a simple heuristic? For now, just slice.
    # Usually "Speed" (Strategy 0) comes first, which is often the best.
    if len(unique_routes) > target_count:
        unique_routes = unique_routes[:target_count]

    return RoutePlanResponse(data={"routes": unique_routes})

