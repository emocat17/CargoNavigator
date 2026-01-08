import pandas as pd
import numpy as np
import re
import math
import os
import glob
from scipy.interpolate import interp1d
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
from contextlib import asynccontextmanager

# 导入路径查找模块
from path_finder import find_all_paths_between_junctions

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

# 全局缓存变量
_bridge_data_cache = None
_cache_timestamp = 0
_cache_file_path = None
_cache_expire_time = 300  # 缓存过期时间（秒），默认5分钟

# 桥梁数据文件夹索引缓存
_bridge_folder_index = None
_folder_index_timestamp = 0
_folder_index_expire_time = 3600  # 文件夹索引缓存过期时间（秒），默认1小时

# 文件编码缓存
_file_encoding_cache = {}  # 文件路径到编码的映射

# 文件内容缓存
_file_content_cache = {}  # 文件路径到内容和时间戳的映射
_file_content_expire_time = 1800  # 文件内容缓存过期时间（秒），默认30分钟

def get_cached_bridge_data(file_path):
    """
    获取缓存的桥梁数据，如果缓存不存在或已过期，则重新加载
    
    参数:
    - file_path: Excel文件路径
    
    返回:
    - 桥梁数据的DataFrame
    """
    global _bridge_data_cache, _cache_timestamp, _cache_file_path
    
    current_time = time.time()
    
    # 检查缓存是否存在、是否过期、文件路径是否变化
    if (_bridge_data_cache is None or 
        current_time - _cache_timestamp > _cache_expire_time or 
        _cache_file_path != file_path):
        
        try:
            print(f"正在加载桥梁数据文件: {file_path}")
            _bridge_data_cache = pd.read_excel(file_path, header=0)
            _cache_timestamp = current_time
            _cache_file_path = file_path
            print(f"成功加载并缓存桥梁数据，共 {len(_bridge_data_cache)} 条记录")
        except Exception as e:
            print(f"加载桥梁数据文件失败: {str(e)}")
            return None
    
    return _bridge_data_cache

def get_bridge_folder_index(base_dir):
    """
    获取桥梁数据文件夹索引，如果缓存不存在或已过期，则重新构建
    
    参数:
    - base_dir: 桥梁数据文件夹根目录
    
    返回:
    - 桩号到文件夹路径的映射字典
    """
    global _bridge_folder_index, _folder_index_timestamp
    
    current_time = time.time()
    
    # 检查缓存是否存在、是否过期
    if (_bridge_folder_index is None or 
        current_time - _folder_index_timestamp > _folder_index_expire_time):
        
        try:
            print(f"正在构建桥梁数据文件夹索引: {base_dir}")
            folder_index = {}
            
            # 遍历桥梁数据文件夹
            for folder_name in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, folder_name)
                if os.path.isdir(folder_path):
                    # 提取桩号（文件夹名中可能包含其他信息，如"K0+15九龙江大桥"）
                    # 我们尝试多种可能的桩号格式
                    station_candidates = [
                        folder_name,  # 完整文件夹名
                        folder_name.split('大桥')[0],  # 去掉"大桥"及之后的内容
                        folder_name.split('桥')[0],  # 去掉"桥"及之后的内容
                        re.sub(r'[^kK0-9+]', '', folder_name)  # 只保留桩号相关字符
                    ]
                    
                    # 将所有可能的桩号格式添加到索引中
                    for station in station_candidates:
                        if station:  # 确保非空
                            folder_index[station.lower()] = folder_path
            
            _bridge_folder_index = folder_index
            _folder_index_timestamp = current_time
            print(f"成功构建桥梁数据文件夹索引，共 {len(folder_index)} 个条目")
        except Exception as e:
            print(f"构建桥梁数据文件夹索引失败: {str(e)}")
            return None
    
    return _bridge_folder_index

def get_file_encoding(file_path):
    """
    获取文件编码，优先从缓存中获取，如果缓存中没有则尝试检测
    
    参数:
    - file_path: 文件路径
    
    返回:
    - 文件编码字符串，如果无法确定则返回None
    """
    global _file_encoding_cache
    
    # 检查缓存中是否有该文件的编码信息
    if file_path in _file_encoding_cache:
        return _file_encoding_cache[file_path]
    
    # 尝试多种编码读取文件
    encodings = ['gbk', 'utf-8', 'gb2312', 'latin1', 'cp1252']
    
    for encoding in encodings:
        try:
            # 只读取第一行来测试编码
            with open(file_path, 'r', encoding=encoding) as f:
                f.readline()
            
            # 如果成功读取，将编码存入缓存并返回
            _file_encoding_cache[file_path] = encoding
            return encoding
        except Exception:
            continue
    
    # 如果所有编码都失败，返回None
    return None

def get_cached_file_content(file_path):
    """
    获取缓存的文件内容，如果缓存不存在或已过期，则重新读取
    
    参数:
    - file_path: 文件路径
    
    返回:
    - 文件内容的DataFrame，如果读取失败则返回None
    """
    global _file_content_cache
    
    current_time = time.time()
    
    # 检查缓存中是否有该文件的内容
    if file_path in _file_content_cache:
        content, timestamp = _file_content_cache[file_path]
        
        # 检查缓存是否过期
        if current_time - timestamp <= _file_content_expire_time:
            return content
    
    # 获取文件编码
    encoding = get_file_encoding(file_path)
    if encoding is None:
        print(f"无法确定文件 {file_path} 的编码")
        return None
    
    try:
        # 读取文件内容
        data = pd.read_csv(file_path, sep=r"\s+", header=None, encoding=encoding,
                          engine="python", on_bad_lines='skip')
        
        # 将内容存入缓存
        _file_content_cache[file_path] = (data, current_time)
        
        return data
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {str(e)}")
        return None

# 定义请求模型
class BridgeEffectRequest(BaseModel):
    loads_ton: List[float]  # 轴重吨数列表
    spacings: List[float]   # 轴距列表
    station: str            # 桩号代码
    highway_code: str = None  # 高速公路代码（可选，用于更精确地定位桥梁）

class FindBridgesRequest(BaseModel):
    junction1: str          # 起点枢纽点名称
    highway_code: str       # 高速公路代码
    junction2: str          # 终点枢纽点名称

class EvaluateRoadSectionRequest(BaseModel):
    junction1: str          # 起点枢纽点名称
    highway_code: str       # 高速公路代码
    junction2: str          # 终点枢纽点名称
    loads_ton: List[float]  # 轴重吨数列表
    spacings: List[float]   # 轴距列表

class EvaluateLongRouteRequest(BaseModel):
    route: List[Dict[str, str]]  # 路线列表，每个元素包含junction和highway_code
    loads_ton: List[float]       # 轴重吨数列表
    spacings: List[float]        # 轴距列表

class FindBridgesByKRangeRequest(BaseModel):
    highway_code: str       # 高速公路代码
    start_k: float          # 起点k值
    end_k: float            # 终点k值

class EvaluateRoadSectionByKRangeRequest(BaseModel):
    highway_code: str       # 高速公路代码
    start_k: float          # 起点k值
    end_k: float            # 终点k值
    loads_ton: List[float]  # 轴重吨数列表
    spacings: List[float]   # 轴距列表

class FindPathRequest(BaseModel):
    start_junction: str     # 起点枢纽点名称
    end_junction: str       # 终点枢纽点名称

class FindAllPathsRequest(BaseModel):
    start_junction: str     # 起点枢纽点名称
    end_junction: str       # 终点枢纽点名称
    max_path_length: Optional[int] = None  # 最大路径长度（可选，用于限制搜索深度）
    return_best_routes: Optional[bool] = True  # 是否返回最佳路线（默认为True）
    top_n: Optional[int] = 3  # 返回的最佳路线数量（默认为3）

class FindAndEvaluateRoutesRequest(BaseModel):
    start_junction: str     # 起点枢纽点名称
    end_junction: str       # 终点枢纽点名称
    loads_ton: List[float]  # 轴重吨数列表
    spacings: List[float]   # 轴距列表
    max_path_length: Optional[int] = None  # 最大路径长度（可选，用于限制搜索深度）
    top_n: Optional[int] = 3  # 返回的最佳路线数量（默认为3）

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
        # 读取枢纽点Excel文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        junctions_file_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'junctions.xlsx')
        
        # 读取Excel数据
        df = pd.read_excel(junctions_file_path)
        
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
    - 多条路线的查找和评估结果
    """
    # 1. 查找所有路径
    all_paths_result = find_all_paths_between_junctions(
        start_junction=start_junction,
        end_junction=end_junction,
        max_path_length=max_path_length,
        return_best_routes=True,
        top_n=top_n
    )
    
    if "error" in all_paths_result:
        return {"error": all_paths_result["error"]}
    
    # 2. 获取最佳路线
    best_routes = all_paths_result["best_routes"]
    
    # 3. 评估每条路线的通行性
    route_evaluations = []
    
    for route in best_routes:
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
                "min_effect_ratio": 0.0
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
            
            route_evaluations.append(route_evaluation)
            continue
        
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
        
        # 记录路线评估结果
        route_evaluation = {
            "path_string": route["path_string"],
            "path_details": route["path_details"],
            "is_passable": evaluation_result["is_passable"],
            "pos_moment_ratio_range": pos_moment_ratio_range,
            "neg_moment_ratio_range": neg_moment_ratio_range,
            "shear_ratio_range": shear_ratio_range,
            "min_effect_ratio": min_effect_ratio,
            "total_bridge_count": evaluation_result.get("total_bridge_count", 0),
            "section_count": evaluation_result.get("section_count", 0),
            "section_evaluations": evaluation_result.get("section_evaluations", [])
        }
        
        # 添加路径枢纽点的经纬度信息
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
        
        route_evaluations.append(route_evaluation)
    
    # 4. 构建结果
    result = {
        "start_junction": start_junction,
        "end_junction": end_junction,
        "route_count": len(route_evaluations),
        "route_evaluations": route_evaluations,
        "loads_ton": loads_ton,
        "spacings": spacings
    }
    
    return result

def calculate_bridge_effect(loads_ton, spacings, station_str, highway_code=None):
    """
    计算桥梁效应比值范围
    
    参数:
    loads_ton: 轴重吨数列表
    spacings: 轴距列表
    station_str: 桩号代码
    highway_code: 高速公路代码（可选，用于更精确地定位桥梁）
    
    返回:
    JSON格式的计算结果，包含:
        - station: 桩号
        - pos_moment_min: 正弯矩最小效应
        - pos_moment_max: 正弯矩最大效应
        - neg_moment_min: 负弯矩最小效应
        - neg_moment_max: 负弯矩最大效应
        - shear_min: 剪力最小效应
        - shear_max: 剪力最大效应
        - damping_factor: 冲击系数
        - pos_moment_ratio_range: 正弯矩效应比值范围
        - neg_moment_ratio_range: 负弯矩效应比值范围
        - shear_ratio_range: 剪力效应比值范围
        - is_passable: 是否满足通行条件
    """
    # 1. 处理车辆参数
    loads = [p * 9.8 for p in loads_ton]  # 轴重kN列表
    axle_positions = np.cumsum([0] + spacings)  # 轴位置列表
    
    # 2. 处理桥梁参数
    station_str = str(station_str).strip()  # 桩号字符串
    
    # 读取 Excel 文件获取桥梁参数
    script_dir = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录
    file_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'bridge_list.xlsx')  # Excel文件路径
    
    # 使用缓存获取桥梁数据
    df = get_cached_bridge_data(file_path)
    if df is None:
        return {
            "error": f"读取桥梁参数文件失败"
        }
    
    # 找到对应的桩号数据
    if highway_code:
        # 如果提供了高速路代码，同时使用桩号和高速路代码进行匹配（不区分大小写）
        station_row = df[(df["桩号"].astype(str).str.lower() == station_str.lower()) & (df["所属高速"].astype(str).str.lower() == highway_code.lower())]
    else:
        # 如果没有提供高速路代码，仅使用桩号进行匹配（向后兼容，不区分大小写）
        station_row = df[df["桩号"].astype(str).str.lower() == station_str.lower()]
    
    if station_row.empty:
        if highway_code:
            return {
                "error": f"未找到桩号 {station_str} 在高速公路 {highway_code} 上的数据"
            }
        else:
            return {
                "error": f"未找到桩号 {station_str} 的数据"
            }
    
    station_row = station_row.iloc[0]  # 获取第一行数据
    
    base_dir = os.path.join(script_dir, '..', '..', 'facility_parameters', 'bridge_data')  # 桥梁数据文件夹路径
    structure_frequency = station_row["结构基频"]  # 结构基频
    pos_moment_design = station_row["正弯矩设计值"]  # 正弯矩设计值
    neg_moment_design = station_row["负弯矩设计值"]  # 负弯矩设计值
    shear_design = station_row["剪力设计值"]  # 剪力设计值
    
    # 3. 冲击系数函数
    def get_damping(f):
        if f < 1.5:
            return 0.05
        elif 1.5 <= f <= 14:
            return 0.1767 * math.log(f) - 0.0157
        else:
            return 0.45
    
    # 获取冲击系数
    try:
        f = float(structure_frequency)
        u = get_damping(f)
    except:
        u = 0
    
    # 4. 找到 txt 文件（使用优化的文件夹索引）
    folder_index = get_bridge_folder_index(base_dir)
    if folder_index is None:
        return {
            "error": "构建桥梁数据文件夹索引失败"
        }
    
    # 尝试从索引中获取文件夹路径
    folder_path = folder_index.get(station_str.lower())
    if folder_path is None:
        # 如果索引中没有找到，尝试使用原始方法
        matched_folders = [f for f in os.listdir(base_dir)
                          if os.path.isdir(os.path.join(base_dir, f))
                          and station_str.lower() in f.lower()]
        
        if not matched_folders:
            print(f"未找到桩号 {station_str} 对应的文件夹")
            return {
                "error": f"{station_str} 文件夹不存在或未找到"
            }
        
        folder_path = os.path.join(base_dir, matched_folders[0])
    
    # print(f"找到桥梁数据文件夹: {folder_path}")
    
    # 优化文件查找，直接构造可能的文件名而不是遍历所有文件
    # 提取桩号部分（文件夹名中的K+数字部分）
    folder_name = os.path.basename(folder_path)
    # 使用正则表达式提取桩号（如K0+15）
    import re
    station_match = re.search(r'K\d+\+\d+', folder_name)
    station_prefix = station_match.group(0) if station_match else folder_name
    
    possible_files = [
        os.path.join(folder_path, f"{folder_name}-正弯矩-大件运输车道.txt"),
        os.path.join(folder_path, f"{station_prefix}{folder_name.replace(station_prefix, '')}-正弯矩-大件运输车道.txt"),
        os.path.join(folder_path, f"{folder_name}-负弯矩-大件运输车道.txt"),
        os.path.join(folder_path, f"{station_prefix}{folder_name.replace(station_prefix, '')}-负弯矩-大件运输车道.txt"),
        os.path.join(folder_path, f"{folder_name}-剪力-大件运输车道.txt"),
        os.path.join(folder_path, f"{station_prefix}{folder_name.replace(station_prefix, '')}-剪力-大件运输车道.txt")
    ]
    
    moment_positive_file = None
    moment_negative_file = None
    shear_file = None
    
    # 检查文件是否存在
    for file_path in possible_files:
        if os.path.exists(file_path):
            if "正弯矩" in file_path: 
                moment_positive_file = file_path
                # print(f"找到正弯矩文件: {os.path.basename(file_path)}")
            elif "负弯矩" in file_path: 
                moment_negative_file = file_path
                # print(f"找到负弯矩文件: {os.path.basename(file_path)}")
            elif "剪力" in file_path: 
                shear_file = file_path
                # print(f"找到剪力文件: {os.path.basename(file_path)}")
    
    # 如果没有找到，尝试使用原始方法
    if moment_positive_file is None or moment_negative_file is None or shear_file is None:
        txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
        for file in txt_files:
            fname = os.path.basename(file)
            if "正弯矩" in fname and moment_positive_file is None: 
                moment_positive_file = file
                # print(f"找到正弯矩文件: {fname}")
            elif "负弯矩" in fname and moment_negative_file is None: 
                moment_negative_file = file
                # print(f"找到负弯矩文件: {fname}")
            elif "剪力" in fname and shear_file is None: 
                shear_file = file
                # print(f"找到剪力文件: {fname}")
    
    # 检查是否找到了所有必要的文件
    if moment_positive_file is None:
        print(f"警告: 未找到正弯矩文件 - 桩号: {station_str}, 文件夹: {folder_path}")
    if moment_negative_file is None:
        print(f"警告: 未找到负弯矩文件 - 桩号: {station_str}, 文件夹: {folder_path}")
    if shear_file is None:
        print(f"警告: 未找到剪力文件 - 桩号: {station_str}, 文件夹: {folder_path}")
    
    # 5. 读取 txt 并计算效应范围（使用优化的文件读取）
    def read_txt(file_path):
        if file_path is None: 
            return None, None
        
        # 使用缓存的文件内容
        data = get_cached_file_content(file_path)
        if data is None:
            print(f"无法读取文件 {file_path}")
            return None, None
        
        try:
            data = data.iloc[3:-2, :4]
            data.columns = data.iloc[0]
            data = data[1:].reset_index(drop=True)
            data = data.drop(data.columns[1], axis=1)
            col2 = data.iloc[:, 1].values
            data = data.loc[~np.r_[False, col2[1:] == col2[:-1]]].reset_index(drop=True)
            n = len(data)
            half_n = n // 2
            part1 = data.iloc[:half_n, :].copy()
            part2 = data.iloc[half_n:2*half_n, :].copy()
            part1["INFLUENCE2"] = part2.iloc[:, -1].values
            part1["INFLUENCE_combined"] = part1.iloc[:, 2:4].astype(float).mean(axis=1)

            # 横坐标和影响线
            x = part1.iloc[:, 1].astype(float).values
            y = part1["INFLUENCE_combined"].astype(float).values
            f_interp = interp1d(x, y, kind='linear', fill_value=0, bounds_error=False)

            # 移动计算效应范围
            step = 0.01
            bridge_start, bridge_end = min(x), max(x)
            max_axle_pos = max(axle_positions)

            # 收集所有效应值
            all_effects = []

            # 正向
            for pos in np.arange(bridge_start - max_axle_pos, bridge_end, step):
                effect = sum(P * f_interp(pos + a) for P, a in zip(loads, axle_positions)
                             if bridge_start <= pos + a <= bridge_end)
                all_effects.append(effect)

            # 反向
            for pos in np.arange(bridge_end + max_axle_pos, bridge_start, -step):
                effect = sum(P * f_interp(pos - a) for P, a in zip(loads, axle_positions)
                             if bridge_start <= pos - a <= bridge_end)
                all_effects.append(effect)

            # 找出最小和最大效应值
            min_effect = min(all_effects)
            max_effect = max(all_effects)

            # 乘以冲击系数
            impact_factor = (1 + u) * 1.1
            return min_effect * impact_factor, max_effect * impact_factor

        except Exception as e:
            print(f"处理 {file_path} 数据时出错: {e}")
            return None, None

    pos_moment_min, pos_moment_max = read_txt(moment_positive_file)
    neg_moment_min, neg_moment_max = read_txt(moment_negative_file)
    shear_min, shear_max = read_txt(shear_file)
    
    # 6. 计算比值范围（设计值/计算效应值）
    # 处理NaN值和零值
    pos_moment_ratio_min = 0
    pos_moment_ratio_max = 0
    neg_moment_ratio_min = 0
    neg_moment_ratio_max = 0
    shear_ratio_min = 0
    shear_ratio_max = 0
    
    # 对于正弯矩
    if pd.notna(pos_moment_min) and pd.notna(pos_moment_max) and pd.notna(pos_moment_design):
        # 使用最大效应值和80%的最大效应值来计算比值范围
        if abs(pos_moment_max) > 0:
            pos_moment_ratio_max = abs(pos_moment_design) / abs(pos_moment_max)
            # 使用80%到120%的最大效应值作为范围
            effect_range_min = abs(pos_moment_max) * 0.8
            effect_range_max = abs(pos_moment_max) * 1.2
            pos_moment_ratio_min = abs(pos_moment_design) / effect_range_max
            pos_moment_ratio_max = abs(pos_moment_design) / effect_range_min
            
            # 确保最小值不大于最大值
            if pos_moment_ratio_min > pos_moment_ratio_max:
                pos_moment_ratio_min, pos_moment_ratio_max = pos_moment_ratio_max, pos_moment_ratio_min
    
    # 对于负弯矩
    if pd.notna(neg_moment_min) and pd.notna(neg_moment_max) and pd.notna(neg_moment_design):
        # 使用最大效应值和80%的最大效应值来计算比值范围
        if abs(neg_moment_max) > 0:
            neg_moment_ratio_max = abs(neg_moment_design) / abs(neg_moment_max)
            # 使用80%到120%的最大效应值作为范围
            effect_range_min = abs(neg_moment_max) * 0.8
            effect_range_max = abs(neg_moment_max) * 1.2
            neg_moment_ratio_min = abs(neg_moment_design) / effect_range_max
            neg_moment_ratio_max = abs(neg_moment_design) / effect_range_min
            
            # 确保最小值不大于最大值
            if neg_moment_ratio_min > neg_moment_ratio_max:
                neg_moment_ratio_min, neg_moment_ratio_max = neg_moment_ratio_max, neg_moment_ratio_min
    
    # 对于剪力
    if pd.notna(shear_min) and pd.notna(shear_max) and pd.notna(shear_design):
        # 使用最大效应值和80%的最大效应值来计算比值范围
        if abs(shear_max) > 0:
            shear_ratio_max = abs(shear_design) / abs(shear_max)
            # 使用80%到120%的最大效应值作为范围
            effect_range_min = abs(shear_max) * 0.8
            effect_range_max = abs(shear_max) * 1.2
            shear_ratio_min = abs(shear_design) / effect_range_max
            shear_ratio_max = abs(shear_design) / effect_range_min
            
            # 确保最小值不大于最大值
            if shear_ratio_min > shear_ratio_max:
                shear_ratio_min, shear_ratio_max = shear_ratio_max, shear_ratio_min
    
    # 判断是否满足通行条件（所有有效比值的最小值均大于1.0）
    valid_ratios = []
    if pos_moment_ratio_min > 0:
        valid_ratios.append(pos_moment_ratio_min)
    if neg_moment_ratio_min > 0:
        valid_ratios.append(neg_moment_ratio_min)
    if shear_ratio_min > 0:
        valid_ratios.append(shear_ratio_min)
    
    all_ratios_valid = len(valid_ratios) > 0 and all(ratio > 1.0 for ratio in valid_ratios)
    
    # 格式化比值范围为字符串，如"1.07~1.92"
    pos_moment_ratio_str = f"{pos_moment_ratio_min:.2f}~{pos_moment_ratio_max:.2f}" if pos_moment_ratio_min > 0 else "0.0"
    neg_moment_ratio_str = f"{neg_moment_ratio_min:.2f}~{neg_moment_ratio_max:.2f}" if neg_moment_ratio_min > 0 else "0.0"
    shear_ratio_str = f"{shear_ratio_min:.2f}~{shear_ratio_max:.2f}" if shear_ratio_min > 0 else "0.0"
    
    # 7. 构建结果字典
    result = {
        "pos_moment_ratio_range": pos_moment_ratio_str,  # 正弯矩效应比值范围
        "neg_moment_ratio_range": neg_moment_ratio_str,  # 负弯矩效应比值范围
        "shear_ratio_range": shear_ratio_str,  # 剪力效应比值范围
        "is_passable": all_ratios_valid,  # 是否满足通行条件
        "station": station_str,  # 桩号
        "pos_moment_min": pos_moment_min,  # 正弯矩最小效应
        "pos_moment_max": pos_moment_max,  # 正弯矩最大效应
        "neg_moment_min": neg_moment_min,  # 负弯矩最小效应
        "neg_moment_max": neg_moment_max,  # 负弯矩最大效应
        "shear_min": shear_min,  # 剪力最小效应
        "shear_max": shear_max,  # 剪力最大效应
        "damping_factor": u  # 冲击系数
        
    }
    
    return result

def extract_k_value(k_string):
    """从k字符串中提取k值，例如从'k1074'提取1074.0"""
    if pd.isna(k_string):
        return None
    
    # 使用正则表达式提取数字部分
    match = re.search(r'k(\d+(\.\d+)?)', str(k_string))
    if match:
        return float(match.group(1))
    return None

def extract_bridge_k_value(bridge_id):
    """从桥梁桩号中提取k值，例如从'k0+15'提取15.0"""
    if pd.isna(bridge_id):
        return None
    
    # 使用正则表达式提取数字部分
    match = re.search(r'k(\d+)\+(\d+)', str(bridge_id))
    if match:
        km = float(match.group(1))
        m = float(match.group(2))
        return km * 1000 + m  # 转换为米
    return None

def load_road_sections():
    """
    加载路段数据
    
    返回:
    - 路段数据列表，每个元素包含junction1, highway_code, junction2
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 直接构造到 Files\effect\facility_parameters\table\road_sections.json 的路径
    road_sections_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'road_sections.json')
    # 规范化路径，处理Windows路径分隔符
    road_sections_path = os.path.normpath(road_sections_path)
    
    try:
        with open(road_sections_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data.get('road_sections', [])
    except Exception as e:
        print(f"加载路段数据失败: {e}")
        return []

def find_path_between_junctions(start_junction, end_junction):
    """
    查找两个枢纽点之间的路径
    
    参数:
    - start_junction: 起点枢纽点名称
    - end_junction: 终点枢纽点名称
    
    返回:
    - 路径信息，包含路径字符串和路径详情
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
    
    # 使用广度优先搜索查找最短路径
    from collections import deque
    
    # 队列中存储 (当前节点, 路径)
    queue = deque([(start_junction, [start_junction])])
    visited = set([start_junction])
    
    while queue:
        current_junction, path = queue.popleft()
        
        # 如果找到终点，构建路径字符串
        if current_junction == end_junction:
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
            
            return {
                "path_string": path_string,
                "path_details": path_details,
                "start_junction": start_junction,
                "end_junction": end_junction,
                "path_length": len(path_details)  # 使用实际添加到path_details中的路段数量
            }
        
        # 遍历所有相邻节点
        for neighbor in graph.get(current_junction, []):
            next_junction = neighbor["junction"]
            
            if next_junction not in visited:
                visited.add(next_junction)
                new_path = path + [next_junction]
                queue.append((next_junction, new_path))
    
    # 如果队列为空仍未找到路径
    return {"error": f"找不到从 {start_junction} 到 {end_junction} 的路径"}

def find_bridges_on_road_section(junction1, highway_code, junction2):
    """
    根据路段（枢纽点1-高速-枢纽点2）查找该路段上的所有桥梁
    
    参数:
    - junction1: 起点枢纽点名称
    - highway_code: 高速公路代码
    - junction2: 终点枢纽点名称
    
    返回:
    - 该路段上的桥梁列表
    """
    
    # 文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bridge_list_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'bridge_list.xlsx')
    
    try:
        # 读取桥梁列表
        bridge_list_df = pd.read_excel(bridge_list_path)
        
        # 首先检查路段是否存在于road_sections.json中
        road_sections = load_road_sections()
        section_exists = False
        
        for section in road_sections:
            if ((section["junction1"] == junction1 and section["junction2"] == junction2) or
                (section["junction1"] == junction2 and section["junction2"] == junction1)) and \
               section["highway_code"] == highway_code:
                section_exists = True
                break
        
        if not section_exists:
            return {"error": f"路段 {junction1}-{highway_code}-{junction2} 不存在"}
        
        # 读取枢纽点位置信息（用于获取k值）
        junctions_positions_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'junctions_positions.xlsx')
        junctions_positions_df = pd.read_excel(junctions_positions_path)
        
        # 提取枢纽点位置信息
        junction1_info = junctions_positions_df[junctions_positions_df['junction_name'] == junction1]
        junction2_info = junctions_positions_df[junctions_positions_df['junction_name'] == junction2]
        
        if junction1_info.empty or junction2_info.empty:
            return {"error": f"找不到枢纽点 {junction1} 或 {junction2} 的位置信息"}
        
        # 获取枢纽点在指定高速公路上的位置
        junction1_on_highway = junction1_info[junction1_info['highway_code'] == highway_code]
        junction2_on_highway = junction2_info[junction2_info['highway_code'] == highway_code]
        
        if junction1_on_highway.empty or junction2_on_highway.empty:
            return {"error": f"枢纽点 {junction1} 或 {junction2} 不在高速公路 {highway_code} 上"}
        
        # 获取k值
        junction1_k = junction1_on_highway.iloc[0]['k_value']
        junction2_k = junction2_on_highway.iloc[0]['k_value']
        
        # 确定起点和终点
        start_k = min(junction1_k, junction2_k)
        end_k = max(junction1_k, junction2_k)
        
        # 提取桥梁的k值
        bridge_list_df['bridge_k_value'] = bridge_list_df['桩号'].apply(extract_bridge_k_value)
        
        # 筛选出在路段范围内且属于指定高速的桥梁
        bridges_on_section = bridge_list_df[
            (bridge_list_df['bridge_k_value'] >= start_k * 1000) & 
            (bridge_list_df['bridge_k_value'] <= end_k * 1000) &
            (bridge_list_df['所属高速'] == highway_code)
        ]
        
        # 只提取桩号信息
        bridge_stations = bridges_on_section['桩号'].tolist()
        
        return {
            "section": f"{junction1}-{highway_code}-{junction2}",
            "start_k": start_k,
            "end_k": end_k,
            "bridges": bridge_stations,
            "count": len(bridge_stations)
        }
        
    except Exception as e:
        return {"error": f"处理数据时出错: {e}"}

def find_bridges_by_k_range(highway_code, start_k, end_k):
    """
    根据k值范围和高速代码查找该路段上的所有桥梁
    
    参数:
    - highway_code: 高速公路代码
    - start_k: 起点k值
    - end_k: 终点k值
    
    返回:
    - 该路段上的桥梁列表
    """
    
    # 1. 检查高速公路是否存在于road_sections.json中
    road_sections = load_road_sections()
    highway_exists = False
    
    for rs in road_sections:
        if rs["highway_code"] == highway_code:
            highway_exists = True
            break
    
    if not highway_exists:
        return {"error": f"高速公路 {highway_code} 不存在"}
    
    # 文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bridge_list_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'bridge_list.xlsx')
    
    try:
        # 读取桥梁列表
        bridge_list_df = pd.read_excel(bridge_list_path)
        
        # 确定起点和终点
        start_k = min(start_k, end_k)
        end_k = max(start_k, end_k)
        
        # 提取桥梁的k值
        bridge_list_df['bridge_k_value'] = bridge_list_df['桩号'].apply(extract_bridge_k_value)
        
        # 筛选出在路段范围内且属于指定高速的桥梁
        bridges_on_section = bridge_list_df[
            (bridge_list_df['bridge_k_value'] >= start_k * 1000) & 
            (bridge_list_df['bridge_k_value'] <= end_k * 1000) &
            (bridge_list_df['所属高速'] == highway_code)
        ]
        
        # 只提取桩号信息
        bridge_stations = bridges_on_section['桩号'].tolist()
        
        return {
            "section": f"k{start_k}-k{end_k} ({highway_code})",
            "start_k": start_k,
            "end_k": end_k,
            "highway_code": highway_code,
            "bridges": bridge_stations,
            "count": len(bridge_stations)
        }
        
    except Exception as e:
        return {"error": f"处理数据时出错: {e}"}

def evaluate_road_section_by_k_range(highway_code, start_k, end_k, loads_ton, spacings):
    """
    根据k值范围评估路段通行性
    
    参数:
    - highway_code: 高速公路代码
    - start_k: 起点k值
    - end_k: 终点k值
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    - 路段通行性评估结果
    """
    # 1. 检查高速公路是否存在于road_sections.json中
    road_sections = load_road_sections()
    highway_exists = False
    
    for rs in road_sections:
        if rs["highway_code"] == highway_code:
            highway_exists = True
            break
    
    if not highway_exists:
        return {"error": f"高速公路 {highway_code} 不存在"}
    
    # 2. 查找路段上的所有桥梁
    bridges_result = find_bridges_by_k_range(highway_code, start_k, end_k)
    
    if "error" in bridges_result:
        return {"error": bridges_result["error"]}
    
    # 3. 逐个计算每座桥梁的效应比值
    bridge_evaluations = []
    all_bridges_passable = True
    
    # 收集所有桥梁的效应比值，用于计算路段的整体效应比值
    all_pos_moment_ratios = []
    all_neg_moment_ratios = []
    all_shear_ratios = []
    
    for bridge_station in bridges_result["bridges"]:
        # 计算桥梁效应，传递高速路代码以更精确地定位桥梁
        bridge_effect = calculate_bridge_effect(loads_ton, spacings, bridge_station, highway_code)
        
        if "error" in bridge_effect:
            # 如果计算某座桥梁时出错，记录错误但继续处理其他桥梁
            bridge_evaluations.append({
                "station": bridge_station,
                "error": bridge_effect["error"],
                "is_passable": False
            })
            all_bridges_passable = False
            continue
        
        # 收集桥梁的效应比值
        if "pos_moment_ratio_range" in bridge_effect and bridge_effect["pos_moment_ratio_range"] != "0.0":
            try:
                pos_ratio_str = bridge_effect["pos_moment_ratio_range"]
                pos_min, pos_max = map(float, pos_ratio_str.split("~"))
                all_pos_moment_ratios.append(pos_min)
                all_pos_moment_ratios.append(pos_max)
            except:
                pass
        
        if "neg_moment_ratio_range" in bridge_effect and bridge_effect["neg_moment_ratio_range"] != "0.0":
            try:
                neg_ratio_str = bridge_effect["neg_moment_ratio_range"]
                neg_min, neg_max = map(float, neg_ratio_str.split("~"))
                all_neg_moment_ratios.append(neg_min)
                all_neg_moment_ratios.append(neg_max)
            except:
                pass
        
        if "shear_ratio_range" in bridge_effect and bridge_effect["shear_ratio_range"] != "0.0":
            try:
                shear_ratio_str = bridge_effect["shear_ratio_range"]
                shear_min, shear_max = map(float, shear_ratio_str.split("~"))
                all_shear_ratios.append(shear_min)
                all_shear_ratios.append(shear_max)
            except:
                pass
        
        # 记录桥梁评估结果
        bridge_evaluations.append({
            "station": bridge_station,
            "is_passable": bridge_effect["is_passable"],
            "pos_moment_ratio_range": bridge_effect["pos_moment_ratio_range"],
            "neg_moment_ratio_range": bridge_effect["neg_moment_ratio_range"],
            "shear_ratio_range": bridge_effect["shear_ratio_range"]
        })
        
        # 如果有任何一座桥梁不满足通行条件，整个路段就不满足
        if not bridge_effect["is_passable"]:
            all_bridges_passable = False
    
    # 4. 计算路段的整体效应比值范围
    pos_moment_ratio_range = "0.0"
    neg_moment_ratio_range = "0.0"
    shear_ratio_range = "0.0"
    
    if all_pos_moment_ratios:
        pos_min = min(all_pos_moment_ratios)
        pos_max = max(all_pos_moment_ratios)
        pos_moment_ratio_range = f"{pos_min:.2f}~{pos_max:.2f}"
    
    if all_neg_moment_ratios:
        neg_min = min(all_neg_moment_ratios)
        neg_max = max(all_neg_moment_ratios)
        neg_moment_ratio_range = f"{neg_min:.2f}~{neg_max:.2f}"
    
    if all_shear_ratios:
        shear_min = min(all_shear_ratios)
        shear_max = max(all_shear_ratios)
        shear_ratio_range = f"{shear_min:.2f}~{shear_max:.2f}"
    
    # 5. 构建结果
    result = {
        "section": f"k{start_k}-k{end_k} ({highway_code})",
        "is_passable": all_bridges_passable,
        "bridge_count": len(bridges_result["bridges"]),
        "bridge_evaluations": bridge_evaluations,
        "loads_ton": loads_ton,
        "spacings": spacings,
        "pos_moment_ratio_range": pos_moment_ratio_range,  # 路段正弯矩效应比值范围
        "neg_moment_ratio_range": neg_moment_ratio_range,  # 路段负弯矩效应比值范围
        "shear_ratio_range": shear_ratio_range  # 路段剪力效应比值范围
    }
    
    return result

def evaluate_road_section_passability(junction1, highway_code, junction2, loads_ton, spacings):
    """
    评估路段通行性
    
    参数:
    - junction1: 起点枢纽点名称
    - highway_code: 高速公路代码
    - junction2: 终点枢纽点名称
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    - 路段通行性评估结果
    """
    # 1. 首先检查路段是否存在于road_sections.json中
    road_sections = load_road_sections()
    section_exists = False
    
    for section in road_sections:
        if ((section["junction1"] == junction1 and section["junction2"] == junction2) or
            (section["junction1"] == junction2 and section["junction2"] == junction1)) and \
           section["highway_code"] == highway_code:
            section_exists = True
            break
    
    if not section_exists:
        return {"error": f"路段 {junction1}-{highway_code}-{junction2} 不存在"}
    
    # 2. 查找路段上的所有桥梁
    bridges_result = find_bridges_on_road_section(junction1, highway_code, junction2)
    
    if "error" in bridges_result:
        return {"error": bridges_result["error"]}
    
    # 3. 逐个计算每座桥梁的效应比值
    bridge_evaluations = []
    all_bridges_passable = True
    
    for bridge_station in bridges_result["bridges"]:
        # 计算桥梁效应，传递高速路代码以更精确地定位桥梁
        bridge_effect = calculate_bridge_effect(loads_ton, spacings, bridge_station, highway_code)
        
        if "error" in bridge_effect:
            # 如果计算某座桥梁时出错，记录错误但继续处理其他桥梁
            bridge_evaluations.append({
                "station": bridge_station,
                "error": bridge_effect["error"],
                "is_passable": False
            })
            all_bridges_passable = False
            continue
        
        # 记录桥梁评估结果
        bridge_evaluations.append({
            "station": bridge_station,
            "is_passable": bridge_effect["is_passable"],
            "pos_moment_ratio_range": bridge_effect["pos_moment_ratio_range"],
            "neg_moment_ratio_range": bridge_effect["neg_moment_ratio_range"],
            "shear_ratio_range": bridge_effect["shear_ratio_range"]
        })
        
        # 如果有任何一座桥梁不满足通行条件，整个路段就不满足
        if not bridge_effect["is_passable"]:
            all_bridges_passable = False
    
    # 4. 构建结果
    result = {
        "section": f"{junction1}-{highway_code}-{junction2}",
        "is_passable": all_bridges_passable,
        "bridge_count": len(bridges_result["bridges"]),
        "bridge_evaluations": bridge_evaluations,
        "loads_ton": loads_ton,
        "spacings": spacings
    }
    
    return result

def evaluate_long_route_passability(route, loads_ton, spacings):
    """
    评估长路段通行性
    
    参数:
    - route: 路线列表，每个元素包含junction和highway_code
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    - 长路段通行性评估结果
    """
    # 1. 解析路线，提取各个路段
    sections = []
    for i in range(len(route) - 1):
        current_point = route[i]
        next_point = route[i + 1]
        
        # 确保每个点都有junction和highway_code
        if 'junction' not in current_point or 'highway_code' not in current_point:
            return {"error": f"路线点 {i+1} 缺少必要的junction或highway_code信息"}
        if 'junction' not in next_point or 'highway_code' not in next_point:
            return {"error": f"路线点 {i+2} 缺少必要的junction或highway_code信息"}
        
        # 添加路段
        sections.append({
            "junction1": current_point['junction'],
            "highway_code": current_point['highway_code'],
            "junction2": next_point['junction']
        })
    
    # 2. 检查所有路段是否存在于road_sections.json中
    road_sections = load_road_sections()
    valid_sections = []
    
    for section in sections:
        section_exists = False
        for rs in road_sections:
            if ((rs["junction1"] == section["junction1"] and rs["junction2"] == section["junction2"]) or
                (rs["junction1"] == section["junction2"] and rs["junction2"] == section["junction1"])) and \
                rs["highway_code"] == section["highway_code"]:
                section_exists = True
                break
        
        if section_exists:
            valid_sections.append(section)
        else:
            # 如果路段不存在，记录错误但继续处理其他路段
            valid_sections.append({
                "junction1": section["junction1"],
                "highway_code": section["highway_code"],
                "junction2": section["junction2"],
                "error": f"路段 {section['junction1']}-{section['highway_code']}-{section['junction2']} 不存在"
            })
    
    # 3. 逐个评估每个路段的通行性
    section_evaluations = []
    all_sections_passable = True
    total_bridge_count = 0
    
    # 收集所有桥梁的效应比值，用于计算长路线的整体效应比值
    all_pos_moment_ratios = []
    all_neg_moment_ratios = []
    all_shear_ratios = []
    
    for section in valid_sections:
        # 如果路段不存在，直接记录错误结果
        if "error" in section:
            section_evaluations.append({
                "section": f"{section['junction1']}-{section['highway_code']}-{section['junction2']}",
                "error": section["error"],
                "is_passable": False,
                "bridge_count": 0
            })
            all_sections_passable = False
            continue
        
        # 评估路段通行性
        section_result = evaluate_road_section_passability(
            junction1=section["junction1"],
            highway_code=section["highway_code"],
            junction2=section["junction2"],
            loads_ton=loads_ton,
            spacings=spacings
        )
        
        if "error" in section_result:
            # 如果评估某个路段时出错，记录错误但继续处理其他路段
            section_evaluations.append({
                "section": f"{section['junction1']}-{section['highway_code']}-{section['junction2']}",
                "error": section_result["error"],
                "is_passable": False,
                "bridge_count": 0
            })
            all_sections_passable = False
            continue
        
        # 收集该路段所有桥梁的效应比值
        for bridge_eval in section_result["bridge_evaluations"]:
            if "pos_moment_ratio_range" in bridge_eval and bridge_eval["pos_moment_ratio_range"] != "0.0":
                try:
                    pos_ratio_str = bridge_eval["pos_moment_ratio_range"]
                    pos_min, pos_max = map(float, pos_ratio_str.split("~"))
                    all_pos_moment_ratios.append(pos_min)
                    all_pos_moment_ratios.append(pos_max)
                except:
                    pass
            
            if "neg_moment_ratio_range" in bridge_eval and bridge_eval["neg_moment_ratio_range"] != "0.0":
                try:
                    neg_ratio_str = bridge_eval["neg_moment_ratio_range"]
                    neg_min, neg_max = map(float, neg_ratio_str.split("~"))
                    all_neg_moment_ratios.append(neg_min)
                    all_neg_moment_ratios.append(neg_max)
                except:
                    pass
            
            if "shear_ratio_range" in bridge_eval and bridge_eval["shear_ratio_range"] != "0.0":
                try:
                    shear_ratio_str = bridge_eval["shear_ratio_range"]
                    shear_min, shear_max = map(float, shear_ratio_str.split("~"))
                    all_shear_ratios.append(shear_min)
                    all_shear_ratios.append(shear_max)
                except:
                    pass
        
        # 记录路段评估结果
        section_evaluations.append({
            "section": section_result["section"],
            "is_passable": section_result["is_passable"],
            "bridge_count": section_result["bridge_count"],
            "bridge_evaluations": section_result["bridge_evaluations"]
        })
        
        # 累加桥梁数量
        total_bridge_count += section_result["bridge_count"]
        
        # 如果有任何一段路不满足通行条件，整个长路段就不满足
        if not section_result["is_passable"]:
            all_sections_passable = False
    
    # 4. 计算长路线的整体效应比值范围
    pos_moment_ratio_range = "0.0"
    neg_moment_ratio_range = "0.0"
    shear_ratio_range = "0.0"
    
    if all_pos_moment_ratios:
        pos_min = min(all_pos_moment_ratios)
        pos_max = max(all_pos_moment_ratios)
        pos_moment_ratio_range = f"{pos_min:.2f}~{pos_max:.2f}"
    
    if all_neg_moment_ratios:
        neg_min = min(all_neg_moment_ratios)
        neg_max = max(all_neg_moment_ratios)
        neg_moment_ratio_range = f"{neg_min:.2f}~{neg_max:.2f}"
    
    if all_shear_ratios:
        shear_min = min(all_shear_ratios)
        shear_max = max(all_shear_ratios)
        shear_ratio_range = f"{shear_min:.2f}~{shear_max:.2f}"
    
    # 5. 构建结果
    result = {
        "route": route,
        "is_passable": all_sections_passable,
        "section_count": len(sections),
        "total_bridge_count": total_bridge_count,
        "section_evaluations": section_evaluations,
        "loads_ton": loads_ton,
        "spacings": spacings,
        "pos_moment_ratio_range": pos_moment_ratio_range,  # 长路线正弯矩效应比值范围
        "neg_moment_ratio_range": neg_moment_ratio_range,  # 长路线负弯矩效应比值范围
        "shear_ratio_range": shear_ratio_range  # 长路线剪力效应比值范围
    }
    
    return result

# 定义API端点
@app.post("/calculate_bridge_effect")
async def api_calculate_bridge_effect(request: BridgeEffectRequest):
    """
    计算桥梁效应比值范围的API端点
    
    参数:
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    - station: 桩号代码
    - highway_code: 高速公路代码（可选，用于更精确地定位桥梁）
    
    返回:
    JSON格式的计算结果
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
    
    参数:
    - junction1: 起点枢纽点名称
    - highway_code: 高速公路代码
    - junction2: 终点枢纽点名称
    
    返回:
    JSON格式的桥梁列表
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
    
    参数:
    - junction1: 起点枢纽点名称
    - highway_code: 高速公路代码
    - junction2: 终点枢纽点名称
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    JSON格式的评估结果
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
    
    参数:
    - route: 路线列表，每个元素包含junction和highway_code
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    JSON格式的长路段通行性评估结果
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
    
    参数:
    - highway_code: 高速公路代码
    - start_k: 起点k值
    - end_k: 终点k值
    
    返回:
    JSON格式的桥梁列表
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
    
    参数:
    - highway_code: 高速公路代码
    - start_k: 起点k值
    - end_k: 终点k值
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    JSON格式的路段通行性评估结果
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
    
    返回:
    - 所有路段信息列表
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
    
    参数:
    - request: 包含起点和终点枢纽点编号的请求
    
    返回:
    - 路径查找结果
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
    
    参数:
    - request: 包含起点和终点枢纽点编号的请求，以及可选的最大路径长度限制、是否返回最佳路线和返回的最佳路线数量
    
    返回:
    - 所有路径或最佳路线的查找结果
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
    
    参数:
    - start_junction: 起点枢纽点名称
    - end_junction: 终点枢纽点名称
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    - max_path_length: 最大路径长度（可选，用于限制搜索深度）
    - top_n: 返回的最佳路线数量（默认为3）
    
    返回:
    - 多条路线的查找和评估结果，包括路径、可通行性、效应比值范围等信息
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

        
# 根路径
@app.get("/refresh_cache")
async def refresh_cache():
    """
    刷新桥梁数据缓存
    
    返回:
    - 刷新结果
    """
    global _bridge_data_cache, _cache_timestamp, _cache_file_path
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, '..', '..', 'facility_parameters', 'table', 'bridge_list.xlsx')
    
    try:
        print(f"正在刷新桥梁数据缓存: {file_path}")
        _bridge_data_cache = pd.read_excel(file_path, header=0)
        _cache_timestamp = time.time()
        _cache_file_path = file_path
        print(f"成功刷新桥梁数据缓存，共 {len(_bridge_data_cache)} 条记录")
        return {
            "success": True,
            "message": f"成功刷新桥梁数据缓存，共 {len(_bridge_data_cache)} 条记录",
            "timestamp": _cache_timestamp
        }
    except Exception as e:
        print(f"刷新桥梁数据缓存失败: {str(e)}")
        return {
            "success": False,
            "error": f"刷新桥梁数据缓存失败: {str(e)}"
        }

@app.get("/cache_status")
async def cache_status():
    """
    获取缓存状态信息
    
    返回:
    - 缓存状态信息
    """
    global _bridge_data_cache, _cache_timestamp, _cache_file_path, _cache_expire_time
    
    current_time = time.time()
    cache_age = current_time - _cache_timestamp if _cache_timestamp > 0 else 0
    
    return {
        "cache_exists": _bridge_data_cache is not None,
        "cache_age_seconds": cache_age,
        "cache_expire_time_seconds": _cache_expire_time,
        "cache_expired": cache_age > _cache_expire_time if _cache_timestamp > 0 else True,
        "file_path": _cache_file_path,
        "record_count": len(_bridge_data_cache) if _bridge_data_cache is not None else 0,
        "current_timestamp": current_time,
        "cache_timestamp": _cache_timestamp
    }

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