#!/usr/bin/env python3
"""
路径查找功能模块
提供查找两个枢纽点之间所有路径的功能
"""

import json
from .file_utils import get_facility_parameters_file


def load_road_sections():
    """
    加载路段数据
    
    返回:
    - 路段数据列表
    """
    road_sections_path = get_facility_parameters_file('road_sections.json')
    
    try:
        with open(road_sections_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('road_sections', [])
    except Exception as e:
        print(f"加载路段数据时出错: {e}")
        return []


def load_optimized_routes():
    """
    加载优化路线数据
    
    返回:
    - 优化路线列表
    """
    optimized_routes_path = get_facility_parameters_file('路线.md')
    
    try:
        with open(optimized_routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 解析路线.md文件，提取优化路线
        routes = []
        lines = content.split('\n')
        
        for line in lines:
            # 跳过注释行和空行
            if line.startswith('#') or not line.strip():
                continue
                
            # 提取路线
            route = line.strip()
            if route:
                routes.append(route)
                
        return routes
    except Exception as e:
        print(f"加载优化路线数据时出错: {e}")
        return []


def calculate_route_similarity(route1, route2):
    """
    计算两条路线的相似度
    
    参数:
    - route1: 路线字符串1
    - route2: 路线字符串2
    
    返回:
    - 相似度分数（0-1之间）
    """
    # 将路线字符串分割成路段
    segments1 = route1.split('-')
    segments2 = route2.split('-')
    
    # 计算相同路段的数量
    common_segments = set(segments1) & set(segments2)
    set_similarity = len(common_segments) / max(len(segments1), len(segments2))
    
    # 计算连续路径片段的相似度
    max_sequence_similarity = 0
    # 检查route1中的所有可能连续片段是否在route2中
    for i in range(len(segments1)):
        for j in range(i+1, min(i+10, len(segments1)+1)):  # 限制最大片段长度为10
            segment = '-'.join(segments1[i:j])
            if segment in route2:
                # 计算片段长度占整个路径的比例
                segment_ratio = (j - i) / len(segments1)
                max_sequence_similarity = max(max_sequence_similarity, segment_ratio)
    
    # 检查route2中的所有可能连续片段是否在route1中
    for i in range(len(segments2)):
        for j in range(i+1, min(i+10, len(segments2)+1)):  # 限制最大片段长度为10
            segment = '-'.join(segments2[i:j])
            if segment in route1:
                # 计算片段长度占整个路径的比例
                segment_ratio = (j - i) / len(segments2)
                max_sequence_similarity = max(max_sequence_similarity, segment_ratio)
    
    # 综合相似度：集合相似度和连续片段相似度的加权平均
    # 连续片段相似度权重更高，因为它更能反映路径的实际匹配程度
    similarity = 0.3 * set_similarity + 0.7 * max_sequence_similarity
    
    return similarity


def find_best_routes(all_paths, optimized_routes, top_n=3):
    """
    从所有路径中找出与优化路线最相似的前N条路线
    
    参数:
    - all_paths: 所有路径列表
    - optimized_routes: 优化路线列表
    - top_n: 返回的最佳路线数量
    
    返回:
    - 最佳路线列表
    """
    if not all_paths:
        return []
    
    # 如果没有优化路线，直接返回前N条路径
    if not optimized_routes:
        return all_paths[:top_n]
    
    # 为每条路径计算与所有优化路线的最大相似度
    route_scores = []
    
    for path in all_paths:
        path_string = path['path_string']
        max_similarity = 0
        
        # 计算与每条优化路线的相似度，取最大值
        for optimized_route in optimized_routes:
            similarity = calculate_route_similarity(path_string, optimized_route)
            max_similarity = max(max_similarity, similarity)
        
        # 添加评分
        route_scores.append({
            'path': path,
            'score': max_similarity
        })
    
    # 按相似度分数从高到低排序
    route_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # 返回前N条最佳路线
    best_routes = [item['path'] for item in route_scores[:top_n]]
    
    # 如果最佳路线数量不足top_n，则添加剩余路线（按路径长度排序）
    if len(best_routes) < top_n:
        # 获取未包含在最佳路线中的其他路线
        other_paths = [item['path'] for item in route_scores[top_n:]]
        # 按路径长度排序
        other_paths.sort(key=lambda x: x['path_length'])
        
        # 添加其他路线直到达到top_n
        needed = top_n - len(best_routes)
        best_routes.extend(other_paths[:needed])
    
    return best_routes


def remove_duplicate_paths(all_paths):
    """
    去除重复的路径
    
    参数:
    - all_paths: 所有路径列表
    
    返回:
    - 去重后的路径列表
    """
    if not all_paths:
        return []
    
    # 使用集合来存储已经见过的路径字符串
    seen_paths = set()
    unique_paths = []
    
    for path in all_paths:
        path_string = path['path_string']
        
        # 如果路径字符串不在集合中，则添加到结果列表
        if path_string not in seen_paths:
            seen_paths.add(path_string)
            unique_paths.append(path)
    
    return unique_paths


def find_all_paths_between_junctions(start_junction, end_junction, max_path_length=None, return_best_routes=True, top_n=3):
    """
    查找两个枢纽点之间的所有路径
    
    参数:
    - start_junction: 起点枢纽点名称
    - end_junction: 终点枢纽点名称
    - max_path_length: 最大路径长度（可选，用于限制搜索深度）
    - return_best_routes: 是否返回最佳路线（默认为True）
    - top_n: 返回的最佳路线数量（默认为3）
    
    返回:
    - 如果return_best_routes为True，返回最佳路线列表
    - 如果return_best_routes为False，返回所有路径列表
    """
    # 加载路段数据
    road_sections = load_road_sections()
    
    if not road_sections:
        return {"error": "无法加载路段数据"}
    
    # 构建图结构：key为枢纽点，value为连接的路段列表
    graph = {}
    for section in road_sections:
        junction1 = section["junction1"]
        junction2 = section["junction2"]
        highway_code = section["highway_code"]
        
        # 添加正向连接
        if junction1 not in graph:
            graph[junction1] = []
        graph[junction1].append({
            "junction": junction2,
            "highway_code": highway_code
        })
        
        # 添加反向连接（因为路段是双向的）
        if junction2 not in graph:
            graph[junction2] = []
        graph[junction2].append({
            "junction": junction1,
            "highway_code": highway_code
        })
    
    # 检查起点和终点是否在图中
    if start_junction not in graph:
        return {"error": f"找不到起点枢纽点: {start_junction}"}
    if end_junction not in graph:
        return {"error": f"找不到终点枢纽点: {end_junction}"}
    
    # 使用深度优先搜索查找所有路径
    all_paths = []
    max_paths = 100  # 限制最大搜索路径数量，避免过多路径导致性能问题
    
    def dfs(current_junction, path, visited):
        # 如果已经找到足够的路径，停止搜索
        if len(all_paths) >= max_paths:
            return
        
        # 如果达到最大路径长度，停止搜索
        if max_path_length is not None and len(path) > max_path_length:
            return
        
        # 如果找到终点，添加到路径列表
        if current_junction == end_junction:
            all_paths.append(path.copy())
            return
        
        # 遍历所有相邻节点
        for neighbor in graph.get(current_junction, []):
            next_junction = neighbor["junction"]
            
            if next_junction not in visited:
                visited.add(next_junction)
                path.append(next_junction)
                
                # 递归搜索
                dfs(next_junction, path, visited)
                
                # 回溯
                path.pop()
                visited.remove(next_junction)
    
    # 从起点开始搜索
    visited = set([start_junction])
    dfs(start_junction, [start_junction], visited)
    
    # 如果没有找到路径
    if not all_paths:
        return {"error": f"找不到从 {start_junction} 到 {end_junction} 的路径"}
    
    # 构建结果
    result_paths = []
    
    for path in all_paths:
        path_details = []
        path_string = start_junction
        
        for i in range(len(path) - 1):
            # 查找连接这两个枢纽点的路段
            for section in road_sections:
                if (section["junction1"] == path[i] and section["junction2"] == path[i+1]) or \
                   (section["junction1"] == path[i+1] and section["junction2"] == path[i]):
                    path_string += f"-{section['highway_code']}-{path[i+1]}"
                    path_details.append({
                        "junction1": path[i],
                        "highway_code": section["highway_code"],
                        "junction2": path[i+1]
                    })
                    break
        
        result_paths.append({
            "path_string": path_string,
            "path_details": path_details,
            "start_junction": start_junction,
            "end_junction": end_junction,
            "path_length": len(path_details)
        })
    
    # 去除重复路径
    unique_paths = remove_duplicate_paths(result_paths)
    
    # 如果需要返回最佳路线
    if return_best_routes:
        # 加载优化路线
        optimized_routes = load_optimized_routes()
        
        # 找出最佳路线
        best_routes = find_best_routes(unique_paths, optimized_routes, top_n)
        
        return {
            "best_routes": best_routes,
            "route_count": len(best_routes),
            "total_unique_routes": len(unique_paths),
            "start_junction": start_junction,
            "end_junction": end_junction
        }
    else:
        # 按路径长度排序
        unique_paths.sort(key=lambda x: x["path_length"])
        
        return {
            "paths": unique_paths,
            "path_count": len(unique_paths),
            "start_junction": start_junction,
            "end_junction": end_junction
        }


def find_shortest_path_between_junctions(start_junction, end_junction):
    """
    查找两个枢纽点之间的最短路径（基于路段数量）
    
    参数:
    - start_junction: 起点枢纽点名称
    - end_junction: 终点枢纽点名称
    
    返回:
    - 最短路径信息，包含路径字符串和路径详情
    """
    # 查找所有路径，不返回最佳路线，而是返回所有路径
    all_paths_result = find_all_paths_between_junctions(start_junction, end_junction, return_best_routes=False)
    
    if "error" in all_paths_result:
        return all_paths_result
    
    # 如果有路径，返回最短的一条
    if all_paths_result["paths"]:
        return all_paths_result["paths"][0]
    
    return {"error": f"找不到从 {start_junction} 到 {end_junction} 的路径"}