#!/usr/bin/env python3
"""
文件处理工具模块
提供文件读取、缓存等功能
"""

import os
import time
import pandas as pd
import re

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


def get_facility_parameters_dir(dir_name):
    """
    获取facility_parameters目录下的子目录路径
    
    参数:
    - dir_name: 子目录名（如'bridge_data'）
    
    返回:
    - 子目录的完整路径
    """
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建目录路径：从tools目录向上三级到达effect目录，然后进入facility_parameters
    dir_path = os.path.join(script_dir, '..', '..', '..', 'facility_parameters', dir_name)
    
    return dir_path


def get_facility_parameters_file(file_name):
    """
    获取facility_parameters/table目录下的文件路径
    
    参数:
    - file_name: 文件名（如'junctions.xlsx'）
    
    返回:
    - 文件的完整路径
    """
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建文件路径：从tools目录向上三级到达effect目录，然后进入facility_parameters/table
    file_path = os.path.join(script_dir, '..', '..', '..', 'facility_parameters', 'table', file_name)
    
    return file_path


def read_facility_parameters_excel(file_name, sheet_name=None):
    """
    读取facility_parameters/table目录下的Excel文件
    
    参数:
    - file_name: 文件名（如'junctions.xlsx'）
    - sheet_name: 工作表名称（可选）
    
    返回:
    - Excel数据的DataFrame，如果读取失败则返回None
    """
    try:
        # 获取文件路径
        file_path = get_facility_parameters_file(file_name)
        
        # 读取Excel文件
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
            
        return df
    except Exception as e:
        print(f"读取Excel文件 {file_name} 失败: {str(e)}")
        return None


def read_junctions_data():
    """
    读取枢纽点数据Excel文件
    
    返回:
    - 枢纽点数据的DataFrame，如果读取失败则返回None
    """
    return read_facility_parameters_excel('junctions.xlsx')


def read_junctions_positions_data():
    """
    读取枢纽点位置信息Excel文件
    
    返回:
    - 枢纽点位置信息的DataFrame，如果读取失败则返回None
    """
    return read_facility_parameters_excel('junctions_positions.xlsx')


def read_bridge_list_data():
    """
    读取桥梁列表Excel文件
    
    返回:
    - 桥梁列表的DataFrame，如果读取失败则返回None
    """
    return read_facility_parameters_excel('bridge_list.xlsx')


def read_markdown_file(file_name):
    """
    读取Markdown文件内容
    
    参数:
    - file_name: 文件名（不含路径）
    
    返回:
    - 文件内容字符串，如果读取失败返回None
    """
    try:
        # 构建文件路径
        file_path = get_facility_parameters_file(file_name)
        
        # 获取文件编码
        encoding = get_file_encoding(file_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
            
        return content
    except Exception as e:
        print(f"读取Markdown文件 {file_name} 失败: {str(e)}")
        return None


def read_text_file(file_name):
    """
    读取文本文件内容
    
    参数:
    - file_name: 文件名（不含路径）
    
    返回:
    - 文件内容字符串，如果读取失败返回None
    """
    try:
        # 构建文件路径
        file_path = get_facility_parameters_file(file_name)
        
        # 获取文件编码
        encoding = get_file_encoding(file_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
            
        return content
    except Exception as e:
        print(f"读取文本文件 {file_name} 失败: {str(e)}")
        return None