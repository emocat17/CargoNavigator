from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# 定义请求模型
class BridgeEffectRequest(BaseModel):
    loads_ton: List[float]  # 轴重吨数列表
    spacings: List[float]   # 轴距列表
    station: str            # 桩号代码
    highway_code: Optional[str] = None  # 高速公路代码（可选，用于更精确地定位桥梁）

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
