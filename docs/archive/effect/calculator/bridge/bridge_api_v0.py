import pandas as pd
import numpy as np
import re
import math
import os
import glob
from scipy.interpolate import interp1d
import json
import random
from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Any, Optional
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from contextlib import asynccontextmanager
import asyncio
import aiohttp

# 导入路径查找模块
from tools.path_finder import find_all_paths_between_junctions, load_road_sections, find_shortest_path_between_junctions

# 导入文件处理工具模块
from tools.file_utils import (
    get_cached_bridge_data, 
    get_bridge_folder_index, 
    get_file_encoding, 
    get_cached_file_content,
    read_junctions_data,
    read_junctions_positions_data,
    read_bridge_list_data
)

# 导入桥梁数据查询工具模块
from tools.bridge_data_query import (
    get_junction_location,
    extract_k_value,
    extract_bridge_k_value,
    find_path_between_junctions,
    find_bridges_on_road_section,
    find_bridges_by_k_range
)

# 导入桥梁效应计算工具模块
from tools.bridge_effect_calculator import (
    calculate_bridge_effect,
    evaluate_road_section_by_k_range,
    evaluate_road_section_passability,
    evaluate_long_route_passability
)

# 导入高德地图工具模块
from tools.amap_utils import add_amap_data_to_routes, find_nearest_junction, async_add_amap_data_to_routes

# 导入路线评估工具模块
from tools.route_evaluator import find_and_evaluate_routes

# 导入路径提取工具模块
from tools.path_extractor import extract_path_details_for_routes

# 导入枢纽映射工具模块
from tools.junction_mapper import map_locations_to_junctions, update_route_locations_with_original_points

# 导入数据模型
from tools.models import (
    BridgeEffectRequest,
    FindBridgesRequest,
    EvaluateRoadSectionRequest,
    EvaluateLongRouteRequest,
    FindBridgesByKRangeRequest,
    EvaluateRoadSectionByKRangeRequest,
    FindPathRequest,
    FindAllPathsRequest,
    FindAndEvaluateRoutesRequest
)

# 导入缓存管理工具
from tools.cache_manager import refresh_bridge_cache, get_cache_status

# 导入AI工具
from tools.ollama_chat import extract_path_string

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理函数
    在应用启动时执行初始化，在应用关闭时执行清理
    """
    # 启动时执行的初始化函数
    print("正在初始化桥梁效应计算API...")
    
    # 预加载桥梁数据文件夹索引
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, '..', '..', 'facility_parameters', 'bridge_data')
    
    try:
        folder_index = get_bridge_folder_index(base_dir)
        if folder_index is not None:
            print(f"成功预加载桥梁数据文件夹索引，共 {len(folder_index)} 个条目")
        else:
            print("预加载桥梁数据文件夹索引失败，将在首次访问时构建")
    except Exception as e:
        print(f"预加载桥梁数据文件夹索引时出错: {str(e)}")
    
    print("桥梁效应计算API初始化完成")
    
    yield  # 应用运行期间
    
    # 关闭时执行的清理函数（如果需要）
    print("桥梁效应计算API正在关闭...")

# 创建FastAPI应用
app = FastAPI(title="桥梁效应计算API", version="1.0.0", lifespan=lifespan)

# 定义API端点
@app.post("/calculate_bridge_effect")
async def api_calculate_bridge_effect(request: BridgeEffectRequest):
    """
    计算桥梁效应比值范围的API端点
    """
    try:
        print(f"收到计算桥梁效应请求: station={request.station}, highway_code={request.highway_code}")
        result = calculate_bridge_effect(
            loads_ton=request.loads_ton,
            spacings=request.spacings,
            station_str=request.station,
            highway_code=request.highway_code
        )
        
        if "error" in result:
            print(f"计算桥梁效应失败: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        print(f"成功计算桥梁效应")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"计算桥梁效应时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"计算过程中发生错误: {str(e)}")

@app.post("/find_bridges_on_road_section")
async def api_find_bridges_on_road_section(request: FindBridgesRequest):
    """
    根据路段查找桥梁的API端点
    """
    try:
        print(f"收到查找桥梁请求: {request.junction1}-{request.highway_code}-{request.junction2}")
        result = find_bridges_on_road_section(
            junction1=request.junction1,
            highway_code=request.highway_code,
            junction2=request.junction2
        )
        
        if "error" in result:
            print(f"查找桥梁失败: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        print(f"成功查找桥梁，找到 {result.get('count', 0)} 座桥梁")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"查找桥梁时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查找桥梁过程中发生错误: {str(e)}")

@app.post("/evaluate_road_section_passability")
async def api_evaluate_road_section_passability(request: EvaluateRoadSectionRequest):
    """
    评估路段通行性的API端点
    """
    try:
        print(f"收到评估路段通行性请求: {request.junction1}-{request.highway_code}-{request.junction2}")
        result = evaluate_road_section_passability(
            junction1=request.junction1,
            highway_code=request.highway_code,
            junction2=request.junction2,
            loads_ton=request.loads_ton,
            spacings=request.spacings
        )
        
        if "error" in result:
            print(f"评估路段通行性失败: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        print(f"成功评估路段通行性: {result.get('passability', '未知')}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"评估路段通行性时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"评估路段通行性过程中发生错误: {str(e)}")

@app.post("/evaluate_long_route_passability")
async def api_evaluate_long_route_passability(request: EvaluateLongRouteRequest):
    """
    评估长路段通行性的API端点
    """
    try:
        result = evaluate_long_route_passability(
            route=request.route,
            loads_ton=request.loads_ton,
            spacings=request.spacings
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估长路段通行性过程中发生错误: {str(e)}")

@app.post("/find_bridges_by_k_range")
async def api_find_bridges_by_k_range(request: FindBridgesByKRangeRequest):
    """
    根据k值范围查找桥梁的API端点
    """
    try:
        result = find_bridges_by_k_range(
            highway_code=request.highway_code,
            start_k=request.start_k,
            end_k=request.end_k
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"根据k值范围查找桥梁过程中发生错误: {str(e)}")

@app.post("/evaluate_road_section_by_k_range")
async def api_evaluate_road_section_by_k_range(request: EvaluateRoadSectionByKRangeRequest):
    """
    根据k值范围评估路段通行性的API端点
    """
    try:
        result = evaluate_road_section_by_k_range(
            highway_code=request.highway_code,
            start_k=request.start_k,
            end_k=request.end_k,
            loads_ton=request.loads_ton,
            spacings=request.spacings
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"根据k值范围评估路段通行性过程中发生错误: {str(e)}")

@app.get("/road_sections")
async def api_get_road_sections():
    """
    获取所有路段信息
    """
    try:
        # 直接从road_sections.json加载路段信息
        road_sections = load_road_sections()
        
        # 构建结果
        result = {
            "road_sections": road_sections,
            "count": len(road_sections)
        }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取路段信息失败: {str(e)}")

@app.post("/api_find_path")
async def api_find_path(request: FindPathRequest):
    """
    查找两个枢纽点之间的路径
    """
    try:
        # 查找路径
        path_result = find_path_between_junctions(
            start_junction=request.start_junction,
            end_junction=request.end_junction
        )
        
        if "error" in path_result:
            raise HTTPException(status_code=400, detail=path_result["error"])
        
        return path_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查找路径失败: {str(e)}")

@app.post("/api_find_all_paths")
async def api_find_all_paths(request: FindAllPathsRequest):
    """
    查找两个枢纽点之间的所有路径
    """
    try:
        # 查找所有路径
        all_paths_result = find_all_paths_between_junctions(
            start_junction=request.start_junction,
            end_junction=request.end_junction,
            max_path_length=request.max_path_length,
            return_best_routes=request.return_best_routes,
            top_n=request.top_n
        )
        
        if "error" in all_paths_result:
            raise HTTPException(status_code=400, detail=all_paths_result["error"])
        
        return all_paths_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查找所有路径失败: {str(e)}")

@app.post("/api_find_and_evaluate_routes")
async def api_find_and_evaluate_routes(request: FindAndEvaluateRoutesRequest):
    """
    查找并评估两个枢纽点之间的多条路线
    """
    try:
        print(f"收到查找并评估路线请求: {request.start_junction} 到 {request.end_junction}")
        result = find_and_evaluate_routes(
            start_junction=request.start_junction,
            end_junction=request.end_junction,
            loads_ton=request.loads_ton,
            spacings=request.spacings,
            max_path_length=request.max_path_length,
            top_n=request.top_n
        )
        
        if "error" in result:
            print(f"查找并评估路线失败: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        print(f"成功查找并评估 {result.get('route_count', 0)} 条路线")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"查找并评估路线时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查找并评估路线过程中发生错误: {str(e)}")

@app.post("/api_find_and_evaluate_routes_with_amap")
async def api_find_and_evaluate_routes_with_amap(request: FindAndEvaluateRoutesRequest):
    """
    查找并评估两个枢纽点之间的多条路线，并返回高德地图API获取的路径信息
    """
    try:
        print(f"收到查找并评估路线请求（含高德地图数据）: {request.start_junction} 到 {request.end_junction}")
        
        # 使用junction_mapper工具模块映射起点和终点到预定义枢纽
        mapped_junctions = map_locations_to_junctions(request.start_junction, request.end_junction)
        
        if "error" in mapped_junctions and mapped_junctions["error"]:
            print(f"枢纽映射失败: {mapped_junctions['error']}")
            raise HTTPException(status_code=400, detail=mapped_junctions["error"])
        
        # 从映射结果中提取所需信息
        start_mapping = mapped_junctions["start_mapping"]
        end_mapping = mapped_junctions["end_mapping"]
        
        start_junction = start_mapping["junction"]
        end_junction = end_mapping["junction"]
        original_start_junction = start_mapping["original_location"]
        original_end_junction = end_mapping["original_location"]
        
        # 使用映射后的枢纽名称调用find_and_evaluate_routes函数
        result = find_and_evaluate_routes(
            start_junction=start_junction,
            end_junction=end_junction,
            loads_ton=request.loads_ton,
            spacings=request.spacings,
            max_path_length=request.max_path_length,
            top_n=request.top_n
        )
        
        if "error" in result:
            print(f"查找并评估路线失败: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
        
        # 添加原始请求信息到结果中
        result["original_start_junction"] = original_start_junction
        result["original_end_junction"] = original_end_junction
        result["mapped_start_junction"] = start_junction
        result["mapped_end_junction"] = end_junction
        
        # 获取所有路线的路径枢纽点经纬度信息
        route_evaluations = result.get('route_evaluations', [])
        if not route_evaluations:
            raise HTTPException(status_code=400, detail="没有找到可用的路线")
        
        # 使用junction_mapper工具模块更新路线的路径位置信息
        route_evaluations = update_route_locations_with_original_points(
            route_evaluations, 
            original_start_junction, 
            original_end_junction,
            start_junction,
            end_junction
        )
        
        # 使用amap_utils中的异步函数为每条路线添加高德地图数据
        route_evaluations = await async_add_amap_data_to_routes(route_evaluations)
        
        # 使用从tools.path_extractor导入的函数并发处理所有路线的路径详情提取
        route_evaluations = await extract_path_details_for_routes(route_evaluations)
        
        # 更新结果中的路线评估数据
        result['route_evaluations'] = route_evaluations
        
        print(f"成功查找并评估 {result.get('route_count', 0)} 条路线，并为每条路线获取高德地图数据")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"查找并评估路线（含高德地图数据）时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查找并评估路线过程中发生错误: {str(e)}")

@app.get("/refresh_cache")
async def api_refresh_cache():
    """
    刷新桥梁数据缓存
    """
    try:
        print(f"正在刷新桥梁数据缓存")
        count = refresh_bridge_cache()
        
        print(f"成功刷新桥梁数据缓存，共 {count} 条记录")
        return {
            "success": True,
            "message": f"成功刷新桥梁数据缓存，共 {count} 条记录",
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"刷新桥梁数据缓存失败: {str(e)}")
        return {
            "success": False,
            "error": f"刷新桥梁数据缓存失败: {str(e)}"
        }

@app.get("/cache_status")
async def api_cache_status():
    """
    获取缓存状态信息
    """
    return get_cache_status()

@app.get("/")
async def root():
    return {"message": "桥梁效应计算API", "version": "1.0.0"}

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
