import pandas as pd
import numpy as np
import re
import math
import os
import glob
from scipy.interpolate import interp1d
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# 导入文件处理工具模块
from .file_utils import (
    get_cached_bridge_data, 
    get_bridge_folder_index, 
    get_cached_file_content
)

# 导入路径查找模块
from .path_finder import load_road_sections

# 导入桥梁数据查询工具模块
from .bridge_data_query import (
    find_bridges_on_road_section,
    find_bridges_by_k_range
)


def calculate_bridge_effect(loads_ton, spacings, station_str, highway_code=None):
    """
    计算桥梁效应比值范围（优化版本）
    
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
    loads = np.array([p * 9.8 for p in loads_ton])  # 轴重kN列表，转换为numpy数组
    axle_positions = np.cumsum([0] + spacings)  # 轴位置列表
    
    # 2. 处理桥梁参数
    station_str = str(station_str).strip()  # 桩号字符串
    
    # 读取 Excel 文件获取桥梁参数
    from .file_utils import get_facility_parameters_file
    file_path = get_facility_parameters_file('bridge_list.xlsx')  # Excel文件路径
    
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
    
    from .file_utils import get_facility_parameters_dir
    base_dir = get_facility_parameters_dir('bridge_data')  # 桥梁数据文件夹路径
    structure_frequency = station_row["结构基频"]  # 结构基频
    pos_moment_design = station_row["正弯矩设计值"]  # 正弯矩设计值
    neg_moment_design = station_row["负弯矩设计值"]  # 负弯矩设计值
    shear_design = station_row["剪力设计值"]  # 剪力设计值
    
    # 3. 冲击系数函数（使用缓存优化）
    @lru_cache(maxsize=100)
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
    
    # 5. 读取 txt 并计算效应范围（使用优化的文件读取和并行计算）
    def read_txt_optimized(file_path):
        """优化版本的文件读取和效应计算函数"""
        if file_path is None: 
            return None, None
        
        # 使用缓存的文件内容
        data = get_cached_file_content(file_path)
        if data is None:
            print(f"无法读取文件 {file_path}")
            return None, None
        
        try:
            # 数据预处理（与原版相同）
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

            # 优化的效应计算 - 使用向量化操作
            bridge_start, bridge_end = min(x), max(x)
            max_axle_pos = max(axle_positions)
            
            # 增大步长以减少计算量，同时保持精度
            step = 0.05  # 从0.01增加到0.05，减少80%的计算量
            
            # 创建位置数组
            forward_positions = np.arange(bridge_start - max_axle_pos, bridge_end, step)
            backward_positions = np.arange(bridge_end + max_axle_pos, bridge_start, -step)
            
            # 向量化计算效应值
            def calculate_effects_vectorized(positions, direction):
                """向量化计算效应值"""
                all_effects = []
                
                # 对于每个位置，计算所有轴的效应
                for pos in positions:
                    if direction == "forward":
                        # 正向：pos + axle_positions
                        axle_pos_on_bridge = pos + axle_positions
                    else:
                        # 反向：pos - axle_positions
                        axle_pos_on_bridge = pos - axle_positions
                    
                    # 检查哪些轴在桥上
                    on_bridge = (axle_pos_on_bridge >= bridge_start) & (axle_pos_on_bridge <= bridge_end)
                    
                    if np.any(on_bridge):
                        # 只计算在桥上的轴的效应
                        valid_axle_positions = axle_pos_on_bridge[on_bridge]
                        valid_loads = loads[on_bridge]
                        
                        # 向量化计算插值
                        bridge_effects = f_interp(valid_axle_positions)
                        effect = np.sum(valid_loads * bridge_effects)
                        all_effects.append(effect)
                
                return all_effects
            
            # 并行计算正向和反向效应
            with ThreadPoolExecutor(max_workers=2) as executor:
                forward_future = executor.submit(calculate_effects_vectorized, forward_positions, "forward")
                backward_future = executor.submit(calculate_effects_vectorized, backward_positions, "backward")
                
                forward_effects = forward_future.result()
                backward_effects = backward_future.result()
            
            # 合并所有效应值
            all_effects = forward_effects + backward_effects
            
            if not all_effects:
                return None, None
            
            # 找出最小和最大效应值
            min_effect = min(all_effects)
            max_effect = max(all_effects)

            # 乘以冲击系数
            impact_factor = (1 + u) * 1.1
            return min_effect * impact_factor, max_effect * impact_factor

        except Exception as e:
            print(f"处理 {file_path} 数据时出错: {e}")
            return None, None
    
    # 并行处理三个文件
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_pos_moment = executor.submit(read_txt_optimized, moment_positive_file)
        future_neg_moment = executor.submit(read_txt_optimized, moment_negative_file)
        future_shear = executor.submit(read_txt_optimized, shear_file)
        
        pos_moment_min, pos_moment_max = future_pos_moment.result()
        neg_moment_min, neg_moment_max = future_neg_moment.result()
        shear_min, shear_max = future_shear.result()
    
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


def evaluate_road_section_by_k_range(highway_code, start_k, end_k, loads_ton, spacings):
    """
    根据桩号范围评估路段通行性
    
    参数:
    - highway_code: 高速公路代码
    - start_k: 起点桩号
    - end_k: 终点桩号
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    - 路段通行性评估结果
    """
    # 1. 检查高速公路是否存在
    from .file_utils import get_facility_parameters_file
    road_sections_file = get_facility_parameters_file('road_sections.json')
    
    try:
        with open(road_sections_file, 'r', encoding='utf-8') as f:
            road_sections = json.load(f)
    except Exception as e:
        return {
            "error": f"读取路段数据失败: {str(e)}"
        }
    
    # 检查高速公路代码是否存在
    highway_exists = any(section.get("highway_code") == highway_code for section in road_sections.get("road_sections", []))
    if not highway_exists:
        return {
            "error": f"高速公路代码 {highway_code} 不存在"
        }
    
    # 2. 查找路段上的桥梁
    bridges_result = find_bridges_by_k_range(highway_code, start_k, end_k)
    
    if "error" in bridges_result:
        return {
            "error": f"查找桥梁失败: {bridges_result['error']}"
        }
    
    bridges = bridges_result.get("bridges", [])
    
    if not bridges:
        return {
            "error": f"在桩号范围 {start_k}-{end_k} 内未找到桥梁"
        }
    
    # 3. 计算每座桥梁的效应
    bridge_results = []
    pos_moment_ratios = []
    neg_moment_ratios = []
    shear_ratios = []
    
    for bridge in bridges:
        station = bridge.get("station", "")
        bridge_highway_code = bridge.get("highway_code", highway_code)
        
        # 计算桥梁效应
        effect_result = calculate_bridge_effect(loads_ton, spacings, station, bridge_highway_code)
        
        if "error" in effect_result:
            bridge_results.append({
                "station": station,
                "highway_code": bridge_highway_code,
                "error": effect_result["error"],
                "is_passable": False
            })
        else:
            # 提取比值范围的最小值
            pos_moment_range = effect_result.get("pos_moment_ratio_range", "0.0")
            neg_moment_range = effect_result.get("neg_moment_ratio_range", "0.0")
            shear_range = effect_result.get("shear_ratio_range", "0.0")
            
            # 解析比值范围字符串，获取最小值
            def parse_ratio_range(range_str):
                if "~" in range_str:
                    parts = range_str.split("~")
                    try:
                        return float(parts[0])
                    except:
                        return 0.0
                return 0.0
            
            pos_moment_min = parse_ratio_range(pos_moment_range)
            neg_moment_min = parse_ratio_range(neg_moment_range)
            shear_min = parse_ratio_range(shear_range)
            
            # 收集比值
            if pos_moment_min > 0:
                pos_moment_ratios.append(pos_moment_min)
            if neg_moment_min > 0:
                neg_moment_ratios.append(neg_moment_min)
            if shear_min > 0:
                shear_ratios.append(shear_min)
            
            bridge_results.append({
                "station": station,
                "highway_code": bridge_highway_code,
                "is_passable": effect_result.get("is_passable", False),
                "pos_moment_ratio_range": pos_moment_range,
                "neg_moment_ratio_range": neg_moment_range,
                "shear_ratio_range": shear_range,
                "pos_moment_min": pos_moment_min,
                "neg_moment_min": neg_moment_min,
                "shear_min": shear_min
            })
    
    # 4. 计算路段整体效应比值范围
    # 使用所有桥梁中的最小比值作为路段的最小比值
    # 使用所有桥梁中的最大比值作为路段的最大比值
    
    # 正弯矩
    if pos_moment_ratios:
        pos_moment_min = min(pos_moment_ratios)
        pos_moment_max = max(pos_moment_ratios) * 1.2  # 稍微扩大范围
    else:
        pos_moment_min = 0
        pos_moment_max = 0
    
    # 负弯矩
    if neg_moment_ratios:
        neg_moment_min = min(neg_moment_ratios)
        neg_moment_max = max(neg_moment_ratios) * 1.2  # 稍微扩大范围
    else:
        neg_moment_min = 0
        neg_moment_max = 0
    
    # 剪力
    if shear_ratios:
        shear_min = min(shear_ratios)
        shear_max = max(shear_ratios) * 1.2  # 稍微扩大范围
    else:
        shear_min = 0
        shear_max = 0
    
    # 判断路段是否可通行
    all_ratios = pos_moment_ratios + neg_moment_ratios + shear_ratios
    is_passable = len(all_ratios) > 0 and all(ratio > 1.0 for ratio in all_ratios)
    
    # 格式化比值范围
    pos_moment_ratio_range = f"{pos_moment_min:.2f}~{pos_moment_max:.2f}" if pos_moment_min > 0 else "0.0"
    neg_moment_ratio_range = f"{neg_moment_min:.2f}~{neg_moment_max:.2f}" if neg_moment_min > 0 else "0.0"
    shear_ratio_range = f"{shear_min:.2f}~{shear_max:.2f}" if shear_min > 0 else "0.0"
    
    # 5. 构建结果
    result = {
        "highway_code": highway_code,
        "start_k": start_k,
        "end_k": end_k,
        "is_passable": is_passable,
        "pos_moment_ratio_range": pos_moment_ratio_range,
        "neg_moment_ratio_range": neg_moment_ratio_range,
        "shear_ratio_range": shear_ratio_range,
        "bridge_count": len(bridges),
        "bridges": bridge_results,
        "min_effect_ratio": min(all_ratios) if all_ratios else 0.0
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
    # 1. 查找路段上的桥梁
    bridges_result = find_bridges_on_road_section(junction1, highway_code, junction2)
    
    if "error" in bridges_result:
        return {
            "error": f"查找桥梁失败: {bridges_result['error']}"
        }
    
    bridges = bridges_result.get("bridges", [])
    
    if not bridges:
        return {
            "error": f"在路段 {junction1}-{junction2} 上未找到桥梁"
        }
    
    # 2. 计算每座桥梁的效应
    bridge_results = []
    pos_moment_ratios = []
    neg_moment_ratios = []
    shear_ratios = []
    
    for bridge in bridges:
        station = bridge.get("station", "")
        bridge_highway_code = bridge.get("highway_code", highway_code)
        
        # 计算桥梁效应
        effect_result = calculate_bridge_effect(loads_ton, spacings, station, bridge_highway_code)
        
        if "error" in effect_result:
            bridge_results.append({
                "station": station,
                "highway_code": bridge_highway_code,
                "error": effect_result["error"],
                "is_passable": False
            })
        else:
            # 提取比值范围的最小值
            pos_moment_range = effect_result.get("pos_moment_ratio_range", "0.0")
            neg_moment_range = effect_result.get("neg_moment_ratio_range", "0.0")
            shear_range = effect_result.get("shear_ratio_range", "0.0")
            
            # 解析比值范围字符串，获取最小值
            def parse_ratio_range(range_str):
                if "~" in range_str:
                    parts = range_str.split("~")
                    try:
                        return float(parts[0])
                    except:
                        return 0.0
                return 0.0
            
            pos_moment_min = parse_ratio_range(pos_moment_range)
            neg_moment_min = parse_ratio_range(neg_moment_range)
            shear_min = parse_ratio_range(shear_range)
            
            # 收集比值
            if pos_moment_min > 0:
                pos_moment_ratios.append(pos_moment_min)
            if neg_moment_min > 0:
                neg_moment_ratios.append(neg_moment_min)
            if shear_min > 0:
                shear_ratios.append(shear_min)
            
            bridge_results.append({
                "station": station,
                "highway_code": bridge_highway_code,
                "is_passable": effect_result.get("is_passable", False),
                "pos_moment_ratio_range": pos_moment_range,
                "neg_moment_ratio_range": neg_moment_range,
                "shear_ratio_range": shear_range,
                "pos_moment_min": pos_moment_min,
                "neg_moment_min": neg_moment_min,
                "shear_min": shear_min
            })
    
    # 3. 计算路段整体效应比值范围
    # 使用所有桥梁中的最小比值作为路段的最小比值
    # 使用所有桥梁中的最大比值作为路段的最大比值
    
    # 正弯矩
    if pos_moment_ratios:
        pos_moment_min = min(pos_moment_ratios)
        pos_moment_max = max(pos_moment_ratios) * 1.2  # 稍微扩大范围
    else:
        pos_moment_min = 0
        pos_moment_max = 0
    
    # 负弯矩
    if neg_moment_ratios:
        neg_moment_min = min(neg_moment_ratios)
        neg_moment_max = max(neg_moment_ratios) * 1.2  # 稍微扩大范围
    else:
        neg_moment_min = 0
        neg_moment_max = 0
    
    # 剪力
    if shear_ratios:
        shear_min = min(shear_ratios)
        shear_max = max(shear_ratios) * 1.2  # 稍微扩大范围
    else:
        shear_min = 0
        shear_max = 0
    
    # 判断路段是否可通行
    all_ratios = pos_moment_ratios + neg_moment_ratios + shear_ratios
    is_passable = len(all_ratios) > 0 and all(ratio > 1.0 for ratio in all_ratios)
    
    # 格式化比值范围
    pos_moment_ratio_range = f"{pos_moment_min:.2f}~{pos_moment_max:.2f}" if pos_moment_min > 0 else "0.0"
    neg_moment_ratio_range = f"{neg_moment_min:.2f}~{neg_moment_max:.2f}" if neg_moment_min > 0 else "0.0"
    shear_ratio_range = f"{shear_min:.2f}~{shear_max:.2f}" if shear_min > 0 else "0.0"
    
    # 4. 构建结果
    result = {
        "junction1": junction1,
        "junction2": junction2,
        "highway_code": highway_code,
        "is_passable": is_passable,
        "pos_moment_ratio_range": pos_moment_ratio_range,
        "neg_moment_ratio_range": neg_moment_ratio_range,
        "shear_ratio_range": shear_ratio_range,
        "bridge_count": len(bridges),
        "bridges": bridge_results,
        "min_effect_ratio": min(all_ratios) if all_ratios else 0.0
    }
    
    return result


def evaluate_long_route_passability(route, loads_ton, spacings):
    """
    评估长路线通行性
    
    参数:
    - route: 路线列表，每个元素包含junction和highway_code
    - loads_ton: 轴重吨数列表
    - spacings: 轴距列表
    
    返回:
    - 长路线通行性评估结果
    """
    if not route or len(route) < 2:
        return {
            "error": "路线至少需要包含两个枢纽点"
        }
    
    # 1. 解析路线，提取路段
    road_sections = []
    for i in range(len(route) - 1):
        junction1 = route[i].get("junction", "")
        highway_code = route[i].get("highway_code", "")
        junction2 = route[i+1].get("junction", "")
        
        if not junction1 or not highway_code or not junction2:
            return {
                "error": f"路线第{i+1}段缺少必要信息"
            }
        
        road_sections.append({
            "junction1": junction1,
            "junction2": junction2,
            "highway_code": highway_code
        })
    
    # 2. 检查所有路段是否存在
    from .file_utils import get_facility_parameters_file
    road_sections_file = get_facility_parameters_file('road_sections.json')
    
    try:
        with open(road_sections_file, 'r', encoding='utf-8') as f:
            road_sections_data = json.load(f)
    except Exception as e:
        return {
            "error": f"读取路段数据失败: {str(e)}"
        }
    
    for section in road_sections:
        highway_code = section["highway_code"]
        # 检查高速公路代码是否存在于路段数据中
        highway_exists = any(section.get("highway_code") == highway_code for section in road_sections_data.get("road_sections", []))
        if not highway_exists:
            return {
                "error": f"高速公路代码 {highway_code} 不存在"
            }
    
    # 3. 评估每个路段的通行性
    section_results = []
    all_pos_moment_ratios = []
    all_neg_moment_ratios = []
    all_shear_ratios = []
    total_bridge_count = 0  # 添加总桥梁计数
    
    for section in road_sections:
        section_result = evaluate_road_section_passability(
            section["junction1"],
            section["highway_code"],
            section["junction2"],
            loads_ton,
            spacings
        )
        
        if "error" in section_result:
            # 如果错误是"未找到桥梁"，则is_passable应为True，因为没有桥梁意味着没有通行性问题
            is_passable = True if "未找到桥梁" in section_result["error"] else False
            
            section_results.append({
                "junction1": section["junction1"],
                "junction2": section["junction2"],
                "highway_code": section["highway_code"],
                "error": section_result["error"],
                "is_passable": is_passable,
                "bridge_count": 0,
                "bridge_evaluations": [],  # 添加桥梁详细评估信息
                "pos_moment_ratio_range": "0.0",
                "neg_moment_ratio_range": "0.0",
                "shear_ratio_range": "0.0"
            })
        else:
            # 收集比值
            pos_moment_range = section_result.get("pos_moment_ratio_range", "0.0")
            neg_moment_range = section_result.get("neg_moment_ratio_range", "0.0")
            shear_range = section_result.get("shear_ratio_range", "0.0")
            
            # 解析比值范围字符串，获取最小值
            def parse_ratio_range(range_str):
                if "~" in range_str:
                    parts = range_str.split("~")
                    try:
                        return float(parts[0])
                    except:
                        return 0.0
                return 0.0
            
            pos_moment_min = parse_ratio_range(pos_moment_range)
            neg_moment_min = parse_ratio_range(neg_moment_range)
            shear_min = parse_ratio_range(shear_range)
            
            # 只有当路段有桥梁时才收集比值
            section_bridge_count = section_result.get("bridge_count", 0)
            if section_bridge_count > 0:
                # 收集比值
                if pos_moment_min > 0:
                    all_pos_moment_ratios.append(pos_moment_min)
                if neg_moment_min > 0:
                    all_neg_moment_ratios.append(neg_moment_min)
                if shear_min > 0:
                    all_shear_ratios.append(shear_min)
            
            # 累加桥梁数量
            total_bridge_count += section_bridge_count
            
            section_results.append({
                "junction1": section["junction1"],
                "junction2": section["junction2"],
                "highway_code": section["highway_code"],
                "is_passable": section_result.get("is_passable", False),
                "pos_moment_ratio_range": pos_moment_range,
                "neg_moment_ratio_range": neg_moment_range,
                "shear_ratio_range": shear_range,
                "bridge_count": section_bridge_count,
                "bridge_evaluations": section_result.get("bridges", []),  # 添加桥梁详细评估信息
                "min_effect_ratio": section_result.get("min_effect_ratio", 0.0)
            })
    
    # 4. 计算长路线整体效应比值范围
    # 使用所有路段中的最小比值作为长路线的最小比值
    # 使用所有路段中的最大比值作为长路线的最大比值
    
    # 正弯矩
    if all_pos_moment_ratios:
        pos_moment_min = min(all_pos_moment_ratios)
        pos_moment_max = max(all_pos_moment_ratios) * 1.2  # 稍微扩大范围
    else:
        pos_moment_min = 0
        pos_moment_max = 0
    
    # 负弯矩
    if all_neg_moment_ratios:
        neg_moment_min = min(all_neg_moment_ratios)
        neg_moment_max = max(all_neg_moment_ratios) * 1.2  # 稍微扩大范围
    else:
        neg_moment_min = 0
        neg_moment_max = 0
    
    # 剪力
    if all_shear_ratios:
        shear_min = min(all_shear_ratios)
        shear_max = max(all_shear_ratios) * 1.2  # 稍微扩大范围
    else:
        shear_min = 0
        shear_max = 0
    
    # 判断长路线是否可通行
    all_ratios = all_pos_moment_ratios + all_neg_moment_ratios + all_shear_ratios
    is_passable = len(all_ratios) > 0 and all(ratio > 1.0 for ratio in all_ratios)
    
    # 格式化比值范围
    pos_moment_ratio_range = f"{pos_moment_min:.2f}~{pos_moment_max:.2f}" if pos_moment_min > 0 else "0.0"
    neg_moment_ratio_range = f"{neg_moment_min:.2f}~{neg_moment_max:.2f}" if neg_moment_min > 0 else "0.0"
    shear_ratio_range = f"{shear_min:.2f}~{shear_max:.2f}" if shear_min > 0 else "0.0"
    
    # 5. 构建结果
    result = {
        "route": route,
        "is_passable": is_passable,
        "pos_moment_ratio_range": pos_moment_ratio_range,
        "neg_moment_ratio_range": neg_moment_ratio_range,
        "shear_ratio_range": shear_ratio_range,
        "section_count": len(road_sections),
        "sections": section_results,
        "section_evaluations": section_results,  # 添加路段评估结果
        "total_bridge_count": total_bridge_count,  # 添加总桥梁数量
        "min_effect_ratio": min(all_ratios) if all_ratios else 0.0
    }
    
    return result