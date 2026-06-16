"""
桥梁数据查询工具模块

该模块包含用于查询桥梁和枢纽点数据的函数，不涉及计算逻辑。
"""

import pandas as pd
import numpy as np
import re
import os
from typing import List, Dict, Any, Optional, Tuple

# 导入文件处理工具模块
from .file_utils import (
    get_cached_bridge_data, 
    get_bridge_folder_index, 
    get_file_encoding, 
    get_cached_file_content,
    read_junctions_data,
    read_junctions_positions_data,
    read_bridge_list_data
)


def get_junction_location(junction_name):
    """
    获取枢纽点的经纬度信息
    
    参数:
    - junction_name: 枢纽点名称
    
    返回:
    - 枢纽点的经纬度信息，格式为 [经度, 纬度]
    - 如果找不到枢纽点，返回 None
    """
    try:
        # 使用封装好的函数读取枢纽点Excel文件
        df = read_junctions_data()
        
        if df is None:
            return None
        
        # 查找枢纽点
        junction_row = df[df['junction_name'] == junction_name]
        
        if junction_row.empty:
            return None
        
        # 获取经纬度信息
        location_str = junction_row.iloc[0]['location']
        
        # 解析经纬度
        if pd.isna(location_str) or location_str == "":
            return None
            
        # 经纬度格式为 "经度,纬度"
        try:
            longitude, latitude = map(float, str(location_str).split(','))
            return [longitude, latitude]
        except:
            return None
            
    except Exception as e:
        print(f"获取枢纽点 {junction_name} 的经纬度信息时出错: {str(e)}")
        return None


def extract_k_value(k_string):
    """
    从桩号字符串中提取数值（以千米为单位）
    
    参数:
    - k_string: 桩号字符串，如 "K15+200"
    
    返回:
    - 桩号数值（千米），如 15.2
    - 如果解析失败，返回 None
    """
    try:
        # 使用正则表达式提取桩号数值
        # 支持格式如 "K15+200", "K0+15", "K10+000" 等
        pattern = r'K(\d+)\+(\d+)'
        match = re.search(pattern, str(k_string).strip(), re.IGNORECASE)
        
        if match:
            km = int(match.group(1))  # 千米部分
            m = int(match.group(2))   # 米部分
            return km + m / 1000.0    # 转换为千米
        else:
            # 尝试其他可能的格式，如纯数字
            try:
                return float(k_string)
            except:
                return None
                
    except Exception as e:
        print(f"提取桩号值时出错: {str(e)}")
        return None


def extract_bridge_k_value(bridge_id):
    """
    从桥梁ID中提取桩号数值
    
    参数:
    - bridge_id: 桥梁ID，通常包含桩号信息
    
    返回:
    - 桩号数值（千米）
    - 如果解析失败，返回 None
    """
    try:
        # 首先尝试直接使用extract_k_value函数
        k_value = extract_k_value(bridge_id)
        if k_value is not None:
            return k_value
            
        # 如果extract_k_value无法解析，尝试从桥梁ID中提取桩号
        # 桥梁ID可能包含桩号信息，如 "K15+200_桥1"
        pattern = r'K(\d+)\+(\d+)'
        match = re.search(pattern, str(bridge_id), re.IGNORECASE)
        
        if match:
            km = int(match.group(1))  # 千米部分
            m = int(match.group(2))   # 米部分
            return km + m / 1000.0    # 转换为千米
        else:
            return None
                
    except Exception as e:
        print(f"从桥梁ID {bridge_id} 提取桩号值时出错: {str(e)}")
        return None


def find_path_between_junctions(start_junction, end_junction):
    """
    查找两个枢纽点之间的路径
    
    参数:
    - start_junction: 起点枢纽点名称
    - end_junction: 终点枢纽点名称
    
    返回:
    - 路径信息，包含路径详情和距离
    - 如果找不到路径，返回错误信息
    """
    try:
        # 导入路径查找模块
        from .path_finder import find_shortest_path_between_junctions
        
        # 使用路径查找模块查找最短路径
        result = find_shortest_path_between_junctions(start_junction, end_junction)
        
        return result
        
    except Exception as e:
        error_msg = f"查找枢纽点 {start_junction} 到 {end_junction} 之间的路径时出错: {str(e)}"
        print(error_msg)
        return {"error": error_msg}


def find_bridges_on_road_section(junction1, highway_code, junction2):
    """
    查找两个枢纽点之间某高速公路上的所有桥梁
    
    参数:
    - junction1: 起点枢纽点名称
    - highway_code: 高速公路代码
    - junction2: 终点枢纽点名称
    
    返回:
    - 包含桥梁信息的字典
    - 如果出错，返回错误信息
    """
    try:
        # 1. 读取桥梁列表数据
        bridge_list = read_bridge_list_data()
        
        if bridge_list is None:
            return {"error": "读取桥梁列表数据失败"}
        
        # 2. 读取枢纽点位置数据
        junctions_positions = read_junctions_positions_data()
        
        if junctions_positions is None:
            return {"error": "读取枢纽点位置数据失败"}
        
        # 3. 获取起点和终点的桩号
        start_junction_row = junctions_positions[junctions_positions['junction_name'] == junction1]
        end_junction_row = junctions_positions[junctions_positions['junction_name'] == junction2]
        
        if start_junction_row.empty or end_junction_row.empty:
            return {"error": f"找不到枢纽点 {junction1} 或 {junction2} 的位置信息"}
        
        start_k = start_junction_row.iloc[0]['k_value']
        end_k = end_junction_row.iloc[0]['k_value']
        
        # 确保起点小于终点
        if start_k > end_k:
            start_k, end_k = end_k, start_k
        
        # 4. 筛选指定高速公路上的桥梁
        highway_bridges = bridge_list[bridge_list['所属高速'] == highway_code].copy()
        
        # 5. 提取桥梁的k值
        highway_bridges['bridge_k_value'] = highway_bridges['桩号'].apply(extract_bridge_k_value)
        
        # 6. 筛选在两个枢纽点之间的桥梁
        bridges_on_section = highway_bridges[
            (highway_bridges['bridge_k_value'] >= start_k) & 
            (highway_bridges['bridge_k_value'] <= end_k)
        ]
        
        # 7. 构建结果
        bridges = []
        for _, bridge in bridges_on_section.iterrows():
            bridges.append({
                "bridge_id": bridge['桩号'],  # 使用桩号作为桥梁ID
                "bridge_name": f"{bridge['所属高速']}_{bridge['桩号']}",  # 组合名称
                "station": bridge['桩号'],
                "highway_code": bridge['所属高速'],
                "bridge_type": bridge['桥型'],
                "span": bridge['跨径'],
                "road_level": bridge['公路等级']
            })
        
        result = {
            "junction1": junction1,
            "junction2": junction2,
            "highway_code": highway_code,
            "start_k": start_k,
            "end_k": end_k,
            "count": len(bridges),
            "bridges": bridges
        }
        
        return result
        
    except Exception as e:
        error_msg = f"查找 {junction1} 到 {junction2} 之间 {highway_code} 高速公路上的桥梁时出错: {str(e)}"
        print(error_msg)
        return {"error": error_msg}


def find_bridges_by_k_range(highway_code, start_k, end_k):
    """
    根据高速公路代码和桩号范围查找桥梁
    
    参数:
    - highway_code: 高速公路代码
    - start_k: 起始桩号（千米）
    - end_k: 结束桩号（千米）
    
    返回:
    - 包含桥梁信息的字典
    - 如果出错，返回错误信息
    """
    try:
        # 1. 读取桥梁列表数据
        bridge_list = read_bridge_list_data()
        
        if bridge_list is None:
            return {"error": "读取桥梁列表数据失败"}
        
        # 2. 确保起始桩号小于结束桩号
        if start_k > end_k:
            start_k, end_k = end_k, start_k
        
        # 3. 筛选指定高速公路上的桥梁
        highway_bridges = bridge_list[bridge_list['所属高速'] == highway_code].copy()
        
        # 4. 提取桥梁的k值
        highway_bridges['bridge_k_value'] = highway_bridges['桩号'].apply(extract_bridge_k_value)
        
        # 5. 筛选在指定桩号范围内的桥梁
        bridges_in_range = highway_bridges[
            (highway_bridges['bridge_k_value'] >= start_k) & 
            (highway_bridges['bridge_k_value'] <= end_k)
        ]
        
        # 6. 构建结果
        bridges = []
        for _, bridge in bridges_in_range.iterrows():
            bridges.append({
                "bridge_id": bridge['桩号'],  # 使用桩号作为桥梁ID
                "bridge_name": f"{bridge['所属高速']}_{bridge['桩号']}",  # 组合名称
                "station": bridge['桩号'],
                "highway_code": bridge['所属高速'],
                "bridge_type": bridge['桥型'],
                "span": bridge['跨径'],
                "road_level": bridge['公路等级']
            })
        
        result = {
            "highway_code": highway_code,
            "start_k": start_k,
            "end_k": end_k,
            "count": len(bridges),
            "bridges": bridges
        }
        
        return result
        
    except Exception as e:
        error_msg = f"根据桩号范围查找 {highway_code} 高速公路上的桥梁时出错: {str(e)}"
        print(error_msg)
        return {"error": error_msg}