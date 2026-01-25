"""
路线评估工具模块

该模块提供了查找并评估路线的功能，包括路线查找、通行性评估和效应比值计算。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from tools.path_finder import find_all_paths_between_junctions
from tools.bridge_effect_calculator import evaluate_long_route_passability
from tools.bridge_data_query import get_junction_location

def process_single_route(route, loads_ton, spacings, start_junction, end_junction):
    """
    处理单条路线的评估，用于并行执行
    """
    # 将路径详情转换为evaluate_long_route_passability所需的格式
    route_for_evaluation = []
    
    for detail in route["path_details"]:
        route_for_evaluation.append({
            "junction": detail["junction1"],
            "highway_code": detail["highway_code"]
        })
    
    # 添加最后一个点
    if route["path_details"]:
        last_detail = route["path_details"][-1]
        route_for_evaluation.append({
            "junction": last_detail["junction2"],
            "highway_code": last_detail["highway_code"]
        })
    
    # 评估路线通行性
    evaluation_result = evaluate_long_route_passability(
        route=route_for_evaluation,
        loads_ton=loads_ton,
        spacings=spacings
    )
    
    if "error" in evaluation_result:
        # 如果评估路线时出错，记录错误但继续处理其他路线
        route_evaluation = {
            "path_string": route["path_string"],
            "path_details": route["path_details"],
            "error": evaluation_result["error"],
            "is_passable": False,
            "pos_moment_ratio_range": "0.0",
            "neg_moment_ratio_range": "0.0",
            "shear_ratio_range": "0.0",
            "min_effect_ratio": 0.0,
            "route_provinces": "error" 
        }
        
        # 即使评估出错，也尝试添加路径枢纽点的经纬度信息
        path_locations = []
        
        # 添加起点经纬度
        start_location = get_junction_location(start_junction)
        if start_location:
            path_locations.append({
                "junction": start_junction,
                "location": start_location
            })
        
        # 添加路径中每个枢纽点的经纬度
        for detail in route["path_details"]:
            # 添加第一个枢纽点
            junction1_location = get_junction_location(detail["junction1"])
            if junction1_location:
                path_locations.append({
                    "junction": detail["junction1"],
                    "location": junction1_location
                })
            
            # 添加第二个枢纽点
            junction2_location = get_junction_location(detail["junction2"])
            if junction2_location:
                path_locations.append({
                    "junction": detail["junction2"],
                    "location": junction2_location
                })
        
        # 添加终点经纬度（如果还没有添加）
        end_location = get_junction_location(end_junction)
        if end_location:
            # 检查终点是否已经在路径中
            end_exists = any(loc["junction"] == end_junction for loc in path_locations)
            if not end_exists:
                path_locations.append({
                    "junction": end_junction,
                    "location": end_location
                })
        
        # 去重（保留第一次出现的记录）
        unique_path_locations = []
        seen_junctions = set()
        for loc in path_locations:
            if loc["junction"] not in seen_junctions:
                unique_path_locations.append(loc)
                seen_junctions.add(loc["junction"])
        
        route_evaluation["path_locations"] = unique_path_locations
        
        return route_evaluation
    
    # 提取效应比值范围
    pos_moment_ratio_range = evaluation_result.get("pos_moment_ratio_range", "0.0")
    neg_moment_ratio_range = evaluation_result.get("neg_moment_ratio_range", "0.0")
    shear_ratio_range = evaluation_result.get("shear_ratio_range", "0.0")
    
    # 计算最小效应比值
    min_effect_ratio = float('inf')
    
    # 解析正弯矩效应比值范围
    if pos_moment_ratio_range != "0.0":
        try:
            pos_min, pos_max = map(float, pos_moment_ratio_range.split("~"))
            min_effect_ratio = min(min_effect_ratio, pos_min)
        except:
            pass
    
    # 解析负弯矩效应比值范围
    if neg_moment_ratio_range != "0.0":
        try:
            neg_min, neg_max = map(float, neg_moment_ratio_range.split("~"))
            min_effect_ratio = min(min_effect_ratio, neg_min)
        except:
            pass
    
    # 解析剪力效应比值范围
    if shear_ratio_range != "0.0":
        try:
            shear_min, shear_max = map(float, shear_ratio_range.split("~"))
            min_effect_ratio = min(min_effect_ratio, shear_min)
        except:
            pass
    
    # 如果没有有效的效应比值，设置为0
    if min_effect_ratio == float('inf'):
        min_effect_ratio = 0.0
    
    # 格式化section_evaluations以匹配example.json的结构
    section_evaluations = []
    for section in evaluation_result.get("section_evaluations", []):
        formatted_section = {
            "section": f"{section.get('junction1', '')}-{section.get('highway_code', '')}-{section.get('junction2', '')}",
            "is_passable": section.get("is_passable", False),
            "bridge_count": section.get("bridge_count", 0),
            "bridge_evaluations": section.get("bridge_evaluations", [])
        }
        
        # 如果有错误信息，添加到结果中
        if "error" in section:
            formatted_section["error"] = section["error"]
        
        # 添加效应比值范围
        if "pos_moment_ratio_range" in section:
            formatted_section["pos_moment_ratio_range"] = section["pos_moment_ratio_range"]
        if "neg_moment_ratio_range" in section:
            formatted_section["neg_moment_ratio_range"] = section["neg_moment_ratio_range"]
        if "shear_ratio_range" in section:
            formatted_section["shear_ratio_range"] = section["shear_ratio_range"]
        if "min_effect_ratio" in section:
            formatted_section["min_effect_ratio"] = section["min_effect_ratio"]
            
        section_evaluations.append(formatted_section)
    
    # 构建最终结果
    route_evaluation = {
        "path_string": route["path_string"],
        "path_details": route["path_details"],
        "is_passable": evaluation_result.get("is_passable", False),
        "pos_moment_ratio_range": pos_moment_ratio_range,
        "neg_moment_ratio_range": neg_moment_ratio_range,
        "shear_ratio_range": shear_ratio_range,
        "min_effect_ratio": min_effect_ratio,
        "total_bridge_count": evaluation_result.get("total_bridge_count", 0),
        "section_count": len(section_evaluations),
        "section_evaluations": section_evaluations,
        "route_provinces": evaluation_result.get("route_provinces", [])
    }
    
    # 添加路径枢纽点经纬度信息
    path_locations = []
    
    # 添加起点经纬度
    start_location = get_junction_location(start_junction)
    if start_location:
        path_locations.append({
            "junction": start_junction,
            "location": start_location
        })
    
    # 添加路径中每个枢纽点的经纬度
    for detail in route["path_details"]:
        # 添加第一个枢纽点
        junction1_location = get_junction_location(detail["junction1"])
        if junction1_location:
            path_locations.append({
                "junction": detail["junction1"],
                "location": junction1_location
            })
        
        # 添加第二个枢纽点
        junction2_location = get_junction_location(detail["junction2"])
        if junction2_location:
            path_locations.append({
                "junction": detail["junction2"],
                "location": junction2_location
            })
    
    # 添加终点经纬度（如果还没有添加）
    end_location = get_junction_location(end_junction)
    if end_location:
        # 检查终点是否已经在路径中
        end_exists = any(loc["junction"] == end_junction for loc in path_locations)
        if not end_exists:
            path_locations.append({
                "junction": end_junction,
                "location": end_location
            })
    
    # 去重（保留第一次出现的记录）
    unique_path_locations = []
    seen_junctions = set()
    for loc in path_locations:
        if loc["junction"] not in seen_junctions:
            unique_path_locations.append(loc)
            seen_junctions.add(loc["junction"])
    
    route_evaluation["path_locations"] = unique_path_locations
    
    return route_evaluation

def find_and_evaluate_routes(start_junction, end_junction, loads_ton, spacings, max_path_length=None, top_n=3):
    """
    查找并评估两个枢纽点之间的多条路线
    
    参数:
    - start_junction: 起点枢纽点名称
    - end_junction: 终点枢纽点名称
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    - max_path_length: 最大路径长度（可选，用于限制搜索深度）
    - top_n: 返回的最佳路线数量（默认为3）
    
    返回:
    - 多条路线的查找和评估结果，只包含可通行的路线
    """
    search_count = max(top_n * 3, 8)  # 至少查找8条路线
    
    # 1. 查找所有路径
    all_paths_result = find_all_paths_between_junctions(
        start_junction=start_junction,
        end_junction=end_junction,
        max_path_length=max_path_length,
        return_best_routes=True,
        top_n=search_count  # 查找更多路线以确保有足够的可通行路线
    )
    
    if "error" in all_paths_result:
        return {"error": all_paths_result["error"]}
    
    # 2. 获取最佳路线
    best_routes = all_paths_result["best_routes"]
    
    # 3. 评估每条路线的通行性
    route_evaluations = []
    
    # 使用线程池并发评估路线
    # 根据路线数量决定线程数，最多16个线程
    max_workers = min(len(best_routes), 16)
    if max_workers < 1:
        max_workers = 1
        
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_route = {
            executor.submit(
                process_single_route, 
                route, 
                loads_ton, 
                spacings, 
                start_junction, 
                end_junction
            ): route 
            for route in best_routes
        }
        
        for future in as_completed(future_to_route):
            try:
                result = future.result()
                if result:
                    route_evaluations.append(result)
            except Exception as e:
                print(f"评估路线时发生异常: {e}")
    
    # 4. 排序和筛选结果
    # 优先选择可通行的路线，然后按最小效应比值降序排列（比值越大越好？通常比值是效应/承载力，越小越好。
    # 这里原来的代码没有明确排序逻辑，但在find_all_paths_between_junctions中已经按距离排序了。
    # 我们这里保持原来的相对顺序，或者重新排序。
    # 为了保持一致性，我们按是否可通行和最小效应比值排序
    # 假设比值越小越安全（如果是效应/抗力）
    
    # 分离可通行和不可通行的路线
    passable_routes = [r for r in route_evaluations if r.get("is_passable", False)]
    impassable_routes = [r for r in route_evaluations if not r.get("is_passable", False)]
    
    # 对可通行路线按最小效应比值升序排序（假设比值越小越好）
    passable_routes.sort(key=lambda x: x.get("min_effect_ratio", 0))
    
    # 对不可通行路线也按最小效应比值升序排序
    impassable_routes.sort(key=lambda x: x.get("min_effect_ratio", 0))
    
    # 合并结果，优先返回可通行路线
    final_routes = passable_routes + impassable_routes
    
    # 只返回前top_n条路线
    final_routes = final_routes[:top_n]
    
    return {
        "start_junction": start_junction,
        "end_junction": end_junction,
        "route_count": len(final_routes),
        "route_evaluations": final_routes
    }
