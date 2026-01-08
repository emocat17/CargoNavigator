import time
from tools.file_utils import read_bridge_list_data

# 全局变量
_bridge_list_cache = None
_cache_timestamp = 0
_cache_file_path = "bridge_list.xlsx"
_cache_expire_time = 3600  # 缓存过期时间（秒）

def refresh_bridge_cache():
    """
    刷新桥梁列表数据缓存
    """
    global _bridge_list_cache, _cache_timestamp, _cache_file_path
    
    try:
        # 使用封装好的函数读取桥梁列表
        data = read_bridge_list_data()
        
        if data is None:
            raise Exception("无法读取桥梁列表数据")
            
        _bridge_list_cache = data
        _cache_timestamp = time.time()
        _cache_file_path = "bridge_list.xlsx"
        return len(_bridge_list_cache)
    except Exception as e:
        raise e

def get_cache_status():
    """
    获取缓存状态信息
    """
    global _bridge_list_cache, _cache_timestamp, _cache_file_path, _cache_expire_time
    
    current_time = time.time()
    cache_age = current_time - _cache_timestamp if _cache_timestamp > 0 else 0
    
    return {
        "cache_exists": _bridge_list_cache is not None,
        "cache_age_seconds": cache_age,
        "cache_expire_time_seconds": _cache_expire_time,
        "cache_expired": cache_age > _cache_expire_time if _cache_timestamp > 0 else True,
        "file_path": _cache_file_path,
        "record_count": len(_bridge_list_cache) if _bridge_list_cache is not None else 0,
        "current_timestamp": current_time,
        "cache_timestamp": _cache_timestamp
    }
