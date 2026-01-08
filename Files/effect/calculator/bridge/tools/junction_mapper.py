#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
枢纽映射工具模块

提供枢纽映射功能，将用户输入的地点名称映射到预定义的枢纽点。
"""

import os
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from .amap_utils import find_nearest_junction


def get_predefined_junctions() -> List[str]:
    """
    获取所有预定义的枢纽名称
    
    返回:
    - 预定义的枢纽名称列表
    """
    # 获取预定义枢纽文件路径
    junctions_file_path = os.path.join(
        os.path.dirname(__file__), 
        '..', '..', '..', 
        'facility_parameters', 'table', 'junctions.xlsx'
    )
    
    predefined_junctions = []
    
    try:
        if os.path.exists(junctions_file_path):
            df = pd.read_excel(junctions_file_path)
            if 'junction_name' in df.columns:
                predefined_junctions = df['junction_name'].tolist()
    except Exception as e:
        print(f"读取预定义枢纽列表失败: {str(e)}")
    
    return predefined_junctions


def map_location_to_junction(location: str) -> Dict[str, Any]:
    """
    将地点名称映射到预定义的枢纽点
    
    参数:
    - location: 地点名称
    
    返回:
    - 包含映射结果的字典，包含以下字段:
      - is_predefined: 是否为预定义枢纽
      - junction: 映射后的枢纽名称
      - original_location: 原始地点名称
      - distance: 距离（如果不是预定义枢纽）
      - error: 错误信息（如果有）
    """
    # 获取所有预定义的枢纽名称
    predefined_junctions = get_predefined_junctions()
    
    result = {
        "is_predefined": False,
        "junction": None,
        "original_location": location,
        "distance": None,
        "error": None
    }
    
    # 如果地点在预定义枢纽列表中，直接返回
    if location in predefined_junctions:
        result["is_predefined"] = True
        result["junction"] = location
        return result
    
    # 如果地点不在预定义枢纽列表中，查找最近的枢纽
    print(f"地点 '{location}' 不在预定义枢纽列表中，查找最近的枢纽...")
    nearest_result = find_nearest_junction(location)
    
    if "error" in nearest_result and nearest_result["error"]:
        result["error"] = nearest_result["error"]
        return result
    
    result["junction"] = nearest_result["nearest_junction"]["name"]
    result["distance"] = nearest_result["distance"]
    
    print(f"地点 '{location}' 映射到枢纽 '{result['junction']}'，距离 {result['distance']/1000:.2f} 公里")
    
    return result


def map_locations_to_junctions(start_location: str, end_location: str) -> Dict[str, Any]:
    """
    将起点和终点名称映射到预定义的枢纽点
    
    参数:
    - start_location: 起点名称
    - end_location: 终点名称
    
    返回:
    - 包含映射结果的字典，包含以下字段:
      - start_mapping: 起点映射结果
      - end_mapping: 终点映射结果
      - error: 错误信息（如果有）
    """
    result = {
        "start_mapping": None,
        "end_mapping": None,
        "error": None
    }
    
    # 映射起点
    start_mapping = map_location_to_junction(start_location)
    if start_mapping["error"]:
        result["error"] = f"起点 '{start_location}' 无法找到对应的枢纽: {start_mapping['error']}"
        return result
    result["start_mapping"] = start_mapping
    
    # 映射终点
    end_mapping = map_location_to_junction(end_location)
    if end_mapping["error"]:
        result["error"] = f"终点 '{end_location}' 无法找到对应的枢纽: {end_mapping['error']}"
        return result
    result["end_mapping"] = end_mapping
    
    return result


def get_location_coordinates(location: str, mapped_junction: str) -> Optional[List[float]]:
    """
    获取地点的经纬度坐标
    
    参数:
    - location: 地点名称
    - mapped_junction: 映射后的枢纽名称
    
    返回:
    - 经纬度坐标列表 [经度, 纬度]，如果不是预定义枢纽且无法获取坐标则返回None
    """
    # 如果地点是预定义枢纽，不需要获取坐标
    if location == mapped_junction:
        return None
    
    # 获取地点的经纬度
    location_result = find_nearest_junction(location)
    if "place_location" in location_result and location_result["place_location"]:
        coords = location_result["place_location"].split(',')
        return [float(coords[0]), float(coords[1])]
    
    return None


def update_route_locations_with_original_points(
    route_evaluations: List[Dict[str, Any]], 
    original_start: str, 
    original_end: str,
    mapped_start: str,
    mapped_end: str
) -> List[Dict[str, Any]]:
    """
    更新路线的路径位置信息，添加原始起点和终点
    
    参数:
    - route_evaluations: 路线评估列表
    - original_start: 原始起点名称
    - original_end: 原始终点名称
    - mapped_start: 映射后的起点枢纽名称
    - mapped_end: 映射后的终点枢纽名称
    
    返回:
    - 更新后的路线评估列表
    """
    # 获取原始起点和终点的经纬度信息
    original_start_location = get_location_coordinates(original_start, mapped_start)
    original_end_location = get_location_coordinates(original_end, mapped_end)
    
    # 为每条路线添加原始起点和终点信息
    for route in route_evaluations:
        # 修改path_locations，添加原始起点和终点的经纬度
        path_locations = route.get('path_locations', [])
        new_path_locations = []
        
        # 添加原始起点
        if original_start_location:
            new_path_locations.append({
                "junction": original_start,
                "location": original_start_location
            })
        
        # 添加原有路径点
        new_path_locations.extend(path_locations)
        
        # 添加原始终点
        if original_end_location:
            new_path_locations.append({
                "junction": original_end,
                "location": original_end_location
            })
        
        # 更新路径位置信息
        route['path_locations'] = new_path_locations
        
        # 修改path_string，添加原始起点和终点
        path_string = route.get('path_string', '')
        if original_start_location and original_end_location:
            # 添加原始起点和终点到路径字符串
            route['path_string'] = f"{original_start}-{path_string}-{original_end}"
    
    return route_evaluations