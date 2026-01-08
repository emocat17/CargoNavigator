"""
路径提取工具模块

该模块提供了从路线中提取路径详情的功能，包括路径字符串提取和路径详情处理。
"""

import asyncio
from tools.ollama_chat import extract_path_string


async def extract_path_details_for_route(route, index):
    """
    为路线提取路径详情
    
    参数:
    - route: 路线字典，包含path_locations和instruction
    - index: 路线索引
    
    返回:
    - 更新后的路线字典，包含path_string_details字段
    """
    path_locations = route.get('path_locations', [])
    instruction = route.get('instruction', '')
    
    # 确保有path_locations和instruction
    if path_locations and instruction:
        # 获取第一个和最后一个位置作为起点和终点
        start_junction = path_locations[0]['junction']
        end_junction = path_locations[-1]['junction']
        
        # 构建path_data字典
        path_data = {
            "start_junction": start_junction,
            "end_junction": end_junction,
            "instruction": instruction
        }
        
        try:
            # 调用extract_path_string函数
            path_string_details = extract_path_string(path_data)
            # 添加到route中
            route['path_string_details'] = path_string_details
            print(f"成功为路线 {index+1} 提取路径详情: {path_string_details[:50]}...")
        except Exception as e:
            print(f"为路线 {index+1} 提取路径详情时出错: {str(e)}")
            route['path_string_details'] = None
    else:
        print(f"路线 {index+1} 缺少path_locations或instruction数据")
        route['path_string_details'] = None
    
    return route


async def extract_path_details_for_routes(route_evaluations):
    """
    为多条路线并发提取路径详情
    
    参数:
    - route_evaluations: 路线评估列表
    
    返回:
    - 更新后的路线评估列表，每条路线包含path_string_details字段
    """
    # 创建异步任务列表，用于并发处理路径详情提取
    tasks = [extract_path_details_for_route(route, i) for i, route in enumerate(route_evaluations)]
    route_evaluations = await asyncio.gather(*tasks)
    
    return route_evaluations