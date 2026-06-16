"""
高德地图API工具模块
提供地名转经纬度、距离计算、最近点查找等功能
"""

import requests
import pandas as pd
import os
import asyncio
import aiohttp
from typing import List, Tuple, Optional, Dict, Any

# 高德地图API密钥
AMAP_API_KEY = "61ded56e661c7338f95ccafd0c4642d5"


def get_lng_lat_amap(address: str) -> Optional[Tuple[float, float]]:
    """
    使用高德地图API根据地址获取经纬度
    
    Args:
        address: 地址字符串
        
    Returns:
        经纬度元组 (longitude, latitude)，如果获取失败则返回None
    """
    # 使用高德地图关键字搜索API
    url = "https://restapi.amap.com/v5/place/text"
    
    params = {
        'keywords': address,
        'key': AMAP_API_KEY,
        'output': 'json',
        'show_fields': 'location'  # 只返回经纬度信息
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') == '1' and data.get('count') != '0':
            # 获取第一个结果的经纬度
            location = data['pois'][0]['location'].split(',')
            longitude = float(location[0])
            latitude = float(location[1])
            return (longitude, latitude)
        else:
            print(f"无法获取地址 '{address}' 的经纬度: {data.get('info', '未知错误')}")
            return None
    except Exception as e:
        print(f"获取地址 '{address}' 的经纬度时出错: {str(e)}")
        return None


def get_driving_distance(origin: str, destination: str) -> int:
    """
    计算两点之间的驾车距离
    
    使用高德地图距离测量API (v3/distance) 计算两点之间的驾车距离
    
    Args:
        origin: 起点经纬度，格式为"经度,纬度"
        destination: 终点经纬度，格式为"经度,纬度"
        
    Returns:
        两点之间的驾车距离（单位：米）
    """
    url = "https://restapi.amap.com/v3/distance"
    params = {
        "origins": origin,
        "destination": destination,
        "type": "1",  # 1：驾车导航距离
        "output": "json",
        "key": AMAP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()

        if data.get("status") == "1" and "results" in data and len(data["results"]) > 0:
            distance = data["results"][0]["distance"]
            return int(distance)
        else:
            raise Exception(f"请求失败：{data.get('info', '未知错误')}")
    except Exception as e:
        print(f"计算距离时出错: {e}")
        return -1


def find_nearest_location(origin: str, location_list: List[str]) -> Dict[str, Any]:
    """
    找出给定点到多个点中距离最近的点
    
    使用高德地图距离测量API一次性计算多个起点到同一个终点的距离，提高效率
    
    Args:
        origin: 起点经纬度，格式为"经度,纬度"
        location_list: 多个目标点的经纬度列表，每个元素格式为"经度,纬度"
        
    Returns:
        包含最近点信息的字典:
        {
            "nearest_location": "经度,纬度",
            "nearest_index": 索引,
            "distance": 距离(米),
            "duration": 预计行驶时间(秒)
        }
    """
    if not location_list:
        return {
            "nearest_location": None,
            "nearest_index": -1,
            "distance": -1,
            "duration": -1,
            "error": "目标位置列表为空"
        }
    
    try:
        # 使用高德地图距离测量API
        # 将多个目标点作为origins，origin作为destination
        origins = "|".join(location_list)
        url = "https://restapi.amap.com/v3/distance"
        
        params = {
            "origins": origins,
            "destination": origin,
            "type": "1",  # 1：驾车导航距离
            "output": "json",
            "key": AMAP_API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "1" and "results" in data:
            results = data["results"]
            
            if not results:
                return {
                    "nearest_location": None,
                    "nearest_index": -1,
                    "distance": -1,
                    "duration": -1,
                    "error": "无法获取任何距离信息"
                }
            
            # 找出距离最短的点
            min_distance = float('inf')
            nearest_location = None
            nearest_index = -1
            nearest_duration = -1
            
            for result in results:
                try:
                    distance = int(result.get("distance", 0))
                    duration = int(result.get("duration", 0))
                    origin_id = int(result.get("origin_id", 0)) - 1  # 转换为0-based索引
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_location = location_list[origin_id]
                        nearest_index = origin_id
                        nearest_duration = duration
                except (ValueError, IndexError) as e:
                    print(f"解析距离结果时出错: {e}")
                    continue
            
            if nearest_location is None:
                return {
                    "nearest_location": None,
                    "nearest_index": -1,
                    "distance": -1,
                    "duration": -1,
                    "error": "无法解析任何有效的距离信息"
                }
            
            return {
                "nearest_location": nearest_location,
                "nearest_index": nearest_index,
                "distance": min_distance,
                "duration": nearest_duration
            }
        else:
            error_info = data.get('info', '未知错误')
            return {
                "nearest_location": None,
                "nearest_index": -1,
                "distance": -1,
                "duration": -1,
                "error": f"高德地图API返回错误: {error_info}"
            }
            
    except Exception as e:
        print(f"查找最近位置时出错: {e}")
        return {
            "nearest_location": None,
            "nearest_index": -1,
            "distance": -1,
            "duration": -1,
            "error": f"请求失败: {str(e)}"
        }


def batch_get_lng_lat(address_list: List[str]) -> Dict[str, Optional[Tuple[float, float]]]:
    """
    批量获取地址的经纬度
    
    使用高德地图地点文本搜索API一次性获取多个地址的经纬度
    
    Args:
        address_list: 地址列表
        
    Returns:
        地址到经纬度的映射字典
    """
    result = {}
    
    # 使用高德地图地点文本搜索API批量获取地址经纬度
    for address in address_list:
        url = "https://restapi.amap.com/v5/place/text"
        
        params = {
            'keywords': address,
            'key': AMAP_API_KEY,
            'output': 'json',
            'show_fields': 'location'  # 只返回经纬度信息
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get('status') == '1' and data.get('count') != '0':
                # 获取第一个结果的经纬度
                location = data['pois'][0]['location'].split(',')
                longitude = float(location[0])
                latitude = float(location[1])
                result[address] = (longitude, latitude)
            else:
                print(f"无法获取地址 '{address}' 的经纬度: {data.get('info', '未知错误')}")
                result[address] = None
        except Exception as e:
            print(f"获取地址 '{address}' 的经纬度时出错: {str(e)}")
            result[address] = None
    
    return result


def get_route_with_amap(path_locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    使用高德地图API获取路径信息
    
    Args:
        path_locations: 路径枢纽点列表，每个元素包含junction和location字段
                       location格式为[经度, 纬度]
    
    Returns:
        包含路径信息的字典:
        {
            "polyline": "经纬度点序列",
            "distance": 距离(米),
            "instruction": "导航指令"
        }
    """
    if not path_locations or len(path_locations) < 2:
        return {
            "polyline": "",
            "distance": 0,
            "instruction": "",
            "error": "路径点数量不足"
        }
    
    # 准备高德地图API请求的起点和终点坐标
    origin = f"{path_locations[0]['location'][0]},{path_locations[0]['location'][1]}"
    destination = f"{path_locations[-1]['location'][0]},{path_locations[-1]['location'][1]}"
    
    # 如果有途经点，添加到请求中
    waypoints = ""
    if len(path_locations) > 2:
        waypoint_coords = [f"{loc['location'][0]},{loc['location'][1]}" for loc in path_locations[1:-1]]
        waypoints = "&waypoints=" + ";".join(waypoint_coords)
    
    # 调用高德地图驾车路径规划API
    api_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}{waypoints}&extensions=all&output=json&key={AMAP_API_KEY}"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        amap_data = response.json()
        
        # 提取路径信息
        if amap_data.get('status') == '1' and 'route' in amap_data and 'paths' in amap_data['route'] and len(amap_data['route']['paths']) > 0:
            path_data = amap_data['route']['paths'][0]
            
            # 提取并合并所有步骤的polyline经纬度标记
            all_path_points = []
            if 'steps' in path_data:
                for step in path_data['steps']:
                    step_polyline = step.get('polyline', '')
                    if step_polyline:
                        # polyline格式为 "lng1,lat1;lng2,lat2;..."
                        points = step_polyline.split(';')
                        for point in points:
                            lng, lat = point.split(',')
                            all_path_points.append([float(lng), float(lat)])
                
                # 将所有点合并为polyline字符串
                polyline = ';'.join([f"{point[0]},{point[1]}" for point in all_path_points])
            else:
                polyline = ""
            
            # 提取总距离（单位：米）
            distance = path_data.get('distance', 0)
            
            # 提取并整合导航指令
            instruction = ""
            if 'steps' in path_data:
                instructions = []
                for step in path_data['steps']:
                    step_instruction = step.get('instruction', '')
                    if step_instruction:
                        instructions.append(step_instruction)
                instruction = "；".join(instructions)
            
            # 检查polyline是否包含原始起点和终点
            if path_locations and len(path_locations) >= 2:
                # 获取原始起点和终点的坐标
                start_coords = path_locations[0]['location']
                end_coords = path_locations[-1]['location']
                
                # 检查polyline的起始点是否接近原始起点
                if polyline:
                    polyline_points = polyline.split(';')
                    if polyline_points:
                        first_point = polyline_points[0].split(',')
                        first_lng, first_lat = float(first_point[0]), float(first_point[1])
                        
                        # 计算起始点与原始起点的距离
                        start_distance = ((first_lng - start_coords[0]) ** 2 + (first_lat - start_coords[1]) ** 2) ** 0.5
                        
                        # 如果距离大于阈值（例如0.01度，约1公里），说明polyline可能不包含原始起点
                        if start_distance > 0.01:
                            print(f"polyline可能不包含原始起点，尝试添加原始起点")
                            # 在polyline前添加原始起点
                            polyline = f"{start_coords[0]},{start_coords[1]};" + polyline
                            
                            # 同时添加起点到第一个枢纽的导航指令
                            if path_locations[0].get('junction') and len(path_locations) > 1 and path_locations[1].get('junction'):
                                start_junction = path_locations[0]['junction']
                                first_junction = path_locations[1]['junction']
                                start_instruction = f"从{start_junction}出发，前往{first_junction}"
                                if instruction:
                                    instruction = start_instruction + "；" + instruction
                                else:
                                    instruction = start_instruction
                    
                        # 检查polyline的结束点是否接近原始终点
                        last_point = polyline_points[-1].split(',')
                        last_lng, last_lat = float(last_point[0]), float(last_point[1])
                        
                        # 计算结束点与原始终点的距离
                        end_distance = ((last_lng - end_coords[0]) ** 2 + (last_lat - end_coords[1]) ** 2) ** 0.5
                        
                        # 如果距离大于阈值，说明polyline可能不包含原始终点
                        if end_distance > 0.01:
                            print(f"polyline可能不包含原始终点，尝试添加原始终点")
                            # 在polyline后添加原始终点
                            polyline = polyline + f";{end_coords[0]},{end_coords[1]}"
                            
                            # 同时添加最后一个枢纽到终点的导航指令
                            if len(path_locations) >= 2 and path_locations[-2].get('junction') and path_locations[-1].get('junction'):
                                last_junction = path_locations[-2]['junction']
                                end_junction = path_locations[-1]['junction']
                                end_instruction = f"从{last_junction}出发，前往{end_junction}"
                                if instruction:
                                    instruction = instruction + "；" + end_instruction
                                else:
                                    instruction = end_instruction
            
            return {
                "polyline": polyline,
                "distance": int(distance),
                "instruction": instruction
            }
        else:
            error_info = amap_data.get('info', '未知错误')
            return {
                "polyline": "",
                "distance": 0,
                "instruction": "",
                "error": f"高德地图API返回错误: {error_info}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "polyline": "",
            "distance": 0,
            "instruction": "",
            "error": f"请求高德地图API失败: {str(e)}"
        }


def find_nearest_junction(place_name: str, junctions_file_path: str = None) -> Dict[str, Any]:
    """
    找出给定地点距离junctions.xlsx中最近的枢纽
    
    Args:
        place_name: 地点名称
        junctions_file_path: junctions.xlsx文件路径，默认为当前目录下的junctions.xlsx
        
    Returns:
        包含最近枢纽信息的字典:
        {
            "place_name": "地点名称",
            "place_location": "经度,纬度",
            "nearest_junction": {
                "name": "枢纽名称",
                "type": "枢纽类型",
                "location": "经度,纬度"
            },
            "distance": 距离(米),
            "duration": 预计行驶时间(秒),
            "error": 错误信息(如果有)
        }
    """
    # 设置默认的junctions.xlsx文件路径
    if junctions_file_path is None:
        junctions_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "facility_parameters", "table", "junctions.xlsx")
    
    result = {
        "place_name": place_name,
        "place_location": None,
        "nearest_junction": None,
        "distance": -1,
        "duration": -1,
        "error": None
    }
    
    try:
        # 1. 获取给定地点的经纬度
        place_coords = get_lng_lat_amap(place_name)
        if place_coords is None:
            result["error"] = f"无法获取地点 '{place_name}' 的经纬度"
            return result
        
        result["place_location"] = f"{place_coords[0]},{place_coords[1]}"
        
        # 2. 读取junctions.xlsx文件
        if not os.path.exists(junctions_file_path):
            result["error"] = f"找不到枢纽文件: {junctions_file_path}"
            return result
        
        # 使用pandas读取Excel文件
        df = pd.read_excel(junctions_file_path)
        
        # 检查必要的列是否存在
        required_columns = ['junction_name', 'junction_type_x000d_', 'location']
        for col in required_columns:
            if col not in df.columns:
                result["error"] = f"枢纽文件缺少必要的列: {col}"
                return result
        
        # 3. 提取所有枢纽的位置信息
        junction_locations = []
        junctions_data = []
        
        for _, row in df.iterrows():
            junction_name = row['junction_name']
            junction_type = row['junction_type_x000d_']
            location = row['location']
            
            # 确保location是字符串格式
            if pd.isna(location):
                continue
                
            junction_locations.append(str(location))
            junctions_data.append({
                "name": junction_name,
                "type": junction_type,
                "location": str(location)
            })
        
        if not junction_locations:
            result["error"] = "没有找到有效的枢纽位置信息"
            return result
        
        # 4. 使用find_nearest_location函数找出最近的枢纽
        nearest_result = find_nearest_location(result["place_location"], junction_locations)
        
        if "error" in nearest_result and nearest_result["error"]:
            result["error"] = nearest_result["error"]
            return result
        
        # 5. 获取最近枢纽的详细信息
        nearest_index = nearest_result["nearest_index"]
        if 0 <= nearest_index < len(junctions_data):
            result["nearest_junction"] = junctions_data[nearest_index]
            result["distance"] = nearest_result["distance"]
            result["duration"] = nearest_result["duration"]
        else:
            result["error"] = "无法获取最近枢纽的详细信息"
        
        return result
        
    except Exception as e:
        result["error"] = f"处理过程中出错: {str(e)}"
        return result


async def async_get_route_with_amap(session: aiohttp.ClientSession, path_locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    异步使用高德地图API获取路径信息
    
    Args:
        session: aiohttp客户端会话
        path_locations: 路径枢纽点列表，每个元素包含junction和location字段
                       location格式为[经度, 纬度]
    
    Returns:
        包含路径信息的字典:
        {
            "polyline": "经纬度点序列",
            "distance": 距离(米),
            "instruction": "导航指令"
        }
    """
    if not path_locations or len(path_locations) < 2:
        return {
            "polyline": "",
            "distance": 0,
            "instruction": "",
            "error": "路径点数量不足"
        }
    
    # 准备高德地图API请求的起点和终点坐标
    origin = f"{path_locations[0]['location'][0]},{path_locations[0]['location'][1]}"
    destination = f"{path_locations[-1]['location'][0]},{path_locations[-1]['location'][1]}"
    
    # 如果有途经点，添加到请求中
    waypoints = ""
    if len(path_locations) > 2:
        waypoint_coords = [f"{loc['location'][0]},{loc['location'][1]}" for loc in path_locations[1:-1]]
        waypoints = "&waypoints=" + ";".join(waypoint_coords)
    
    # 调用高德地图驾车路径规划API
    api_url = f"https://restapi.amap.com/v3/direction/driving?origin={origin}&destination={destination}{waypoints}&extensions=all&output=json&key={AMAP_API_KEY}"
    
    try:
        async with session.get(api_url) as response:
            response.raise_for_status()
            amap_data = await response.json()
            
            # 提取路径信息
            if amap_data.get('status') == '1' and 'route' in amap_data and 'paths' in amap_data['route'] and len(amap_data['route']['paths']) > 0:
                path_data = amap_data['route']['paths'][0]
                
                # 提取并合并所有步骤的polyline经纬度标记
                all_path_points = []
                if 'steps' in path_data:
                    for step in path_data['steps']:
                        step_polyline = step.get('polyline', '')
                        if step_polyline:
                            # polyline格式为 "lng1,lat1;lng2,lat2;..."
                            points = step_polyline.split(';')
                            for point in points:
                                lng, lat = point.split(',')
                                all_path_points.append([float(lng), float(lat)])
                    
                    # 将所有点合并为polyline字符串
                    polyline = ';'.join([f"{point[0]},{point[1]}" for point in all_path_points])
                else:
                    polyline = ""
                
                # 提取总距离（单位：米）
                distance = path_data.get('distance', 0)
                
                # 提取并整合导航指令
                instruction = ""
                if 'steps' in path_data:
                    instructions = []
                    for step in path_data['steps']:
                        step_instruction = step.get('instruction', '')
                        if step_instruction:
                            instructions.append(step_instruction)
                    instruction = "；".join(instructions)
                
                # 检查polyline是否包含原始起点和终点
                if path_locations and len(path_locations) >= 2:
                    # 获取原始起点和终点的坐标
                    start_coords = path_locations[0]['location']
                    end_coords = path_locations[-1]['location']
                    
                    # 检查polyline的起始点是否接近原始起点
                    if polyline:
                        polyline_points = polyline.split(';')
                        if polyline_points:
                            first_point = polyline_points[0].split(',')
                            first_lng, first_lat = float(first_point[0]), float(first_point[1])
                            
                            # 计算起始点与原始起点的距离
                            start_distance = ((first_lng - start_coords[0]) ** 2 + (first_lat - start_coords[1]) ** 2) ** 0.5
                            
                            # 如果距离大于阈值（例如0.01度，约1公里），说明polyline可能不包含原始起点
                            if start_distance > 0.01:
                                print(f"polyline可能不包含原始起点，尝试添加原始起点")
                                # 在polyline前添加原始起点
                                polyline = f"{start_coords[0]},{start_coords[1]};" + polyline
                                
                                # 同时添加起点到第一个枢纽的导航指令
                                if path_locations[0].get('junction') and len(path_locations) > 1 and path_locations[1].get('junction'):
                                    start_junction = path_locations[0]['junction']
                                    first_junction = path_locations[1]['junction']
                                    start_instruction = f"从{start_junction}出发，前往{first_junction}"
                                    if instruction:
                                        instruction = start_instruction + "；" + instruction
                                    else:
                                        instruction = start_instruction
                            
                            # 检查polyline的结束点是否接近原始终点
                            last_point = polyline_points[-1].split(',')
                            last_lng, last_lat = float(last_point[0]), float(last_point[1])
                            
                            # 计算结束点与原始终点的距离
                            end_distance = ((last_lng - end_coords[0]) ** 2 + (last_lat - end_coords[1]) ** 2) ** 0.5
                            
                            # 如果距离大于阈值，说明polyline可能不包含原始终点
                            if end_distance > 0.01:
                                print(f"polyline可能不包含原始终点，尝试添加原始终点")
                                # 在polyline后添加原始终点
                                polyline = polyline + f";{end_coords[0]},{end_coords[1]}"
                                
                                # 同时添加最后一个枢纽到终点的导航指令
                                if len(path_locations) >= 2 and path_locations[-2].get('junction') and path_locations[-1].get('junction'):
                                    last_junction = path_locations[-2]['junction']
                                    end_junction = path_locations[-1]['junction']
                                    end_instruction = f"从{last_junction}出发，前往{end_junction}"
                                    if instruction:
                                        instruction = instruction + "；" + end_instruction
                                    else:
                                        instruction = end_instruction
                
                return {
                    "polyline": polyline,
                    "distance": int(distance),
                    "instruction": instruction
                }
            else:
                error_info = amap_data.get('info', '未知错误')
                return {
                    "polyline": "",
                    "distance": 0,
                    "instruction": "",
                    "error": f"高德地图API返回错误: {error_info}"
                }
                
    except aiohttp.ClientError as e:
        return {
            "polyline": "",
            "distance": 0,
            "instruction": "",
            "error": f"请求高德地图API失败: {str(e)}"
        }


async def async_add_amap_data_to_routes(route_evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    异步为多条路线添加高德地图数据
    
    Args:
        route_evaluations: 路线评估结果列表
        
    Returns:
        添加了高德地图数据的路线评估结果列表
    """
    # 创建aiohttp客户端会话
    connector = aiohttp.TCPConnector(limit=100)  # 限制最大连接数
    timeout = aiohttp.ClientTimeout(total=30)    # 设置超时时间
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 创建任务列表，每个任务处理一条路线
        tasks = []
        for i, route in enumerate(route_evaluations):
            task = asyncio.create_task(process_single_route_async(session, route, i+1))
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_routes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"处理路线 {i+1} 时发生异常: {str(result)}")
                # 如果发生异常，保留原始路线数据，但添加错误信息
                route = route_evaluations[i].copy()
                route['polyline'] = ""
                route['distance'] = 0
                route['instruction'] = ""
                route['error'] = str(result)
                processed_routes.append(route)
            else:
                processed_routes.append(result)
        
        return processed_routes


async def process_single_route_async(session: aiohttp.ClientSession, route: Dict[str, Any], route_index: int) -> Dict[str, Any]:
    """
    异步处理单条路线的高德地图数据
    
    Args:
        session: aiohttp客户端会话
        route: 单条路线数据
        route_index: 路线索引（用于日志）
        
    Returns:
        添加了高德地图数据的路线
    """
    path_locations = route.get('path_locations', [])
    
    if not path_locations or len(path_locations) < 2:
        print(f"路线 {route_index} 没有足够的经纬度信息")
        route['polyline'] = ""
        route['distance'] = 0
        route['instruction'] = ""
        return route
    
    # 调用高德地图API获取路径信息
    amap_result = await async_get_route_with_amap(session, path_locations)
    
    # 添加路径信息到当前路线中
    route['polyline'] = amap_result.get('polyline', "")
    route['distance'] = amap_result.get('distance', 0)
    route['instruction'] = amap_result.get('instruction', "")
    
    # 检查polyline是否包含原始起点和终点
    if path_locations and len(path_locations) >= 2:
        # 获取原始起点和终点的坐标
        start_coords = path_locations[0]['location']
        end_coords = path_locations[-1]['location']
        
        # 检查polyline的起始点是否接近原始起点
        if route['polyline']:
            polyline_points = route['polyline'].split(';')
            if polyline_points:
                first_point = polyline_points[0].split(',')
                first_lng, first_lat = float(first_point[0]), float(first_point[1])
                
                # 计算起始点与原始起点的距离
                start_distance = ((first_lng - start_coords[0]) ** 2 + (first_lat - start_coords[1]) ** 2) ** 0.5
                
                # 如果距离大于阈值（例如0.01度，约1公里），说明polyline可能不包含原始起点
                if start_distance > 0.01:
                    print(f"路线 {route_index} 的polyline可能不包含原始起点，尝试添加原始起点")
                    # 在polyline前添加原始起点
                    route['polyline'] = f"{start_coords[0]},{start_coords[1]};" + route['polyline']
                    
                    # 同时添加起点到第一个枢纽的导航指令
                    if path_locations[0].get('junction') and path_locations[1].get('junction'):
                        start_junction = path_locations[0]['junction']
                        first_junction = path_locations[1]['junction']
                        start_instruction = f"从{start_junction}出发，前往{first_junction}"
                        if route['instruction']:
                            route['instruction'] = start_instruction + "；" + route['instruction']
                        else:
                            route['instruction'] = start_instruction
                
                # 检查polyline的结束点是否接近原始终点
                last_point = polyline_points[-1].split(',')
                last_lng, last_lat = float(last_point[0]), float(last_point[1])
                
                # 计算结束点与原始终点的距离
                end_distance = ((last_lng - end_coords[0]) ** 2 + (last_lat - end_coords[1]) ** 2) ** 0.5
                
                # 如果距离大于阈值，说明polyline可能不包含原始终点
                if end_distance > 0.01:
                    print(f"路线 {route_index} 的polyline可能不包含原始终点，尝试添加原始终点")
                    # 在polyline后添加原始终点
                    route['polyline'] = route['polyline'] + f";{end_coords[0]},{end_coords[1]}"
                    
                    # 同时添加最后一个枢纽到终点的导航指令
                    if len(path_locations) >= 2 and path_locations[-2].get('junction') and path_locations[-1].get('junction'):
                        last_junction = path_locations[-2]['junction']
                        end_junction = path_locations[-1]['junction']
                        end_instruction = f"从{last_junction}出发，前往{end_junction}"
                        if route['instruction']:
                            route['instruction'] = route['instruction'] + "；" + end_instruction
                        else:
                            route['instruction'] = end_instruction
    
    if 'error' in amap_result:
        print(f"获取路线 {route_index} 的高德地图数据失败: {amap_result['error']}")
    else:
        print(f"成功获取路线 {route_index} 的高德地图数据，距离: {route['distance']}米")
    
    return route


def add_amap_data_to_routes(route_evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为多条路线添加高德地图数据
    
    Args:
        route_evaluations: 路线评估结果列表
        
    Returns:
        添加了高德地图数据的路线评估结果列表
    """
    for i, route in enumerate(route_evaluations):
        path_locations = route.get('path_locations', [])
        
        if not path_locations or len(path_locations) < 2:
            print(f"路线 {i+1} 没有足够的经纬度信息")
            route['polyline'] = ""
            route['distance'] = 0
            route['instruction'] = ""
            continue
        
        # 调用高德地图API获取路径信息
        amap_result = get_route_with_amap(path_locations)
        
        # 添加路径信息到当前路线中
        route['polyline'] = amap_result.get('polyline', "")
        route['distance'] = amap_result.get('distance', 0)
        route['instruction'] = amap_result.get('instruction', "")
        
        # 检查polyline是否包含原始起点和终点
        if path_locations and len(path_locations) >= 2:
            # 获取原始起点和终点的坐标
            start_coords = path_locations[0]['location']
            end_coords = path_locations[-1]['location']
            
            # 检查polyline的起始点是否接近原始起点
            if route['polyline']:
                polyline_points = route['polyline'].split(';')
                if polyline_points:
                    first_point = polyline_points[0].split(',')
                    first_lng, first_lat = float(first_point[0]), float(first_point[1])
                    
                    # 计算起始点与原始起点的距离
                    start_distance = ((first_lng - start_coords[0]) ** 2 + (first_lat - start_coords[1]) ** 2) ** 0.5
                    
                    # 如果距离大于阈值（例如0.01度，约1公里），说明polyline可能不包含原始起点
                    if start_distance > 0.01:
                        print(f"路线 {i+1} 的polyline可能不包含原始起点，尝试添加原始起点")
                        # 在polyline前添加原始起点
                        route['polyline'] = f"{start_coords[0]},{start_coords[1]};" + route['polyline']
                        
                        # 同时添加起点到第一个枢纽的导航指令
                        if path_locations[0].get('junction') and path_locations[1].get('junction'):
                            start_junction = path_locations[0]['junction']
                            first_junction = path_locations[1]['junction']
                            start_instruction = f"从{start_junction}出发，前往{first_junction}"
                            if route['instruction']:
                                route['instruction'] = start_instruction + "；" + route['instruction']
                            else:
                                route['instruction'] = start_instruction
                
                    # 检查polyline的结束点是否接近原始终点
                    last_point = polyline_points[-1].split(',')
                    last_lng, last_lat = float(last_point[0]), float(last_point[1])
                    
                    # 计算结束点与原始终点的距离
                    end_distance = ((last_lng - end_coords[0]) ** 2 + (last_lat - end_coords[1]) ** 2) ** 0.5
                    
                    # 如果距离大于阈值，说明polyline可能不包含原始终点
                    if end_distance > 0.01:
                        print(f"路线 {i+1} 的polyline可能不包含原始终点，尝试添加原始终点")
                        # 在polyline后添加原始终点
                        route['polyline'] = route['polyline'] + f";{end_coords[0]},{end_coords[1]}"
                        
                        # 同时添加最后一个枢纽到终点的导航指令
                        if len(path_locations) >= 2 and path_locations[-2].get('junction') and path_locations[-1].get('junction'):
                            last_junction = path_locations[-2]['junction']
                            end_junction = path_locations[-1]['junction']
                            end_instruction = f"从{last_junction}出发，前往{end_junction}"
                            if route['instruction']:
                                route['instruction'] = route['instruction'] + "；" + end_instruction
                            else:
                                route['instruction'] = end_instruction
        
        if 'error' in amap_result:
            print(f"获取路线 {i+1} 的高德地图数据失败: {amap_result['error']}")
        else:
            print(f"成功获取路线 {i+1} 的高德地图数据，距离: {route['distance']}米")
    
    return route_evaluations


# 示例使用
if __name__ == "__main__":
    # 示例1: 获取地址的经纬度


    location = get_lng_lat_amap("福建省众岩工程机械有限公司")
    print(f"福建省众岩工程机械有限公司 的经纬度为: {location}")
    
    location = get_lng_lat_amap("厦门千秋业水泥制品有限公司")
    print(f"厦门千秋业水泥制品有限公司 的经纬度为: {location}")
    
    # 示例2: 计算两点之间的距离
    origin = "116.481028,39.989643"  # 北京
    destination = "114.465302,40.004717"  # 张家口
    distance = get_driving_distance(origin, destination)
    print(f"从起点到终点的驾车距离为: {distance} 米")
    
    # 示例3: 找出最近的位置
    origin = "116.481028,39.989643"
    locations = [
        "114.465302,40.004717",  # 张家口
        "117.190182,39.125596",  # 天津
        "116.405285,39.904989"   # 北京
    ]
    nearest = find_nearest_location(origin, locations)
    print(f"距离起点最近的位置是: {nearest['nearest_location']}, 距离: {nearest['distance']} 米")
    print(f"预计行驶时间: {nearest['duration']}秒")
    
    # 示例4: 查找最近枢纽
    print("\n示例4: 查找最近枢纽")
    place_name = "福建省众岩工程机械有限公司"
    nearest_junction = find_nearest_junction(place_name)
    if "error" in nearest_junction and nearest_junction["error"]:
        print(f"错误: {nearest_junction['error']}")
    else:
        print(f"地点: {nearest_junction['place_name']}")
        print(f"地点坐标: {nearest_junction['place_location']}")
        print(f"最近枢纽: {nearest_junction['nearest_junction']['name']}")
        print(f"枢纽类型: {nearest_junction['nearest_junction']['type']}")
        print(f"枢纽坐标: {nearest_junction['nearest_junction']['location']}")
        print(f"距离: {nearest_junction['distance']/1000:.2f} 公里")
        print(f"预计行驶时间: {nearest_junction['duration']/60:.2f} 分钟")

    # 示例5: 查找另一个地点的最近枢纽
    print("\n示例5: 查找另一个地点的最近枢纽")
    place_name2 = "厦门千秋业水泥制品有限公司"
    nearest_junction2 = find_nearest_junction(place_name2)
    if "error" in nearest_junction2 and nearest_junction2["error"]:
        print(f"错误: {nearest_junction2['error']}")
    else:
        print(f"地点: {nearest_junction2['place_name']}")
        print(f"地点坐标: {nearest_junction2['place_location']}")
        print(f"最近枢纽: {nearest_junction2['nearest_junction']['name']}")
        print(f"枢纽类型: {nearest_junction2['nearest_junction']['type']}")
        print(f"枢纽坐标: {nearest_junction2['nearest_junction']['location']}")
        print(f"距离: {nearest_junction2['distance']/1000:.2f} 公里")
        print(f"预计行驶时间: {nearest_junction2['duration']/60:.2f} 分钟")