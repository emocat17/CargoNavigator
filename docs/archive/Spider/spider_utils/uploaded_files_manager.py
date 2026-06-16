import json
import os
import re
from datetime import datetime

def sort_uploaded_files_by_date(json_file_path):
    """
    对已上传文件列表按日期排序，最新的在前
    
    Args:
        json_file_path (str): JSON文件路径
    
    Returns:
        list: 排序后的文件列表
    """
    # 如果文件不存在，返回空列表
    if not os.path.exists(json_file_path):
        return []
    
    # 读取文件内容
    with open(json_file_path, 'r', encoding='utf-8') as f:
        files = json.load(f)
    
    # 定义排序函数，从文件名中提取日期时间
    def extract_datetime(filename):
        # 文件名格式示例: 2024-05-15_14-59-14_S58晋长高速_K1_200___K0_800.md
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
        if match:
            date_str = match.group(1)  # 2024-05-15
            time_str = match.group(2)  # 14-59-14
            # 将时间字符串转换为datetime对象
            datetime_str = f"{date_str} {time_str.replace('-', ':')}"
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        return datetime.min  # 如果无法提取日期，返回最小日期
    
    # 按日期排序，最新的在前
    sorted_files = sorted(files, key=extract_datetime, reverse=True)
    
    # 写回文件
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_files, f, ensure_ascii=False, indent=2)
    
    return sorted_files

def is_file_uploaded(json_file_path, filename):
    """
    检查文件是否已在已上传列表中
    
    Args:
        json_file_path (str): JSON文件路径
        filename (str): 要检查的文件名
    
    Returns:
        bool: 是否已上传
    """
    # 如果文件不存在，返回False
    if not os.path.exists(json_file_path):
        return False
    
    # 读取文件内容
    with open(json_file_path, 'r', encoding='utf-8') as f:
        uploaded_files = json.load(f)
    
    # 检查文件是否在列表中
    return filename in uploaded_files

def add_uploaded_file(json_file_path, filename):
    """
    添加文件到已上传列表
    
    Args:
        json_file_path (str): JSON文件路径
        filename (str): 要添加的文件名
    
    Returns:
        bool: 是否添加成功
    """
    # 读取现有文件列表
    uploaded_files = []
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            uploaded_files = json.load(f)
    
    # 如果文件已存在，不添加
    if filename in uploaded_files:
        return False
    
    # 添加新文件
    uploaded_files.append(filename)
    
    # 按日期排序
    def extract_datetime(file_name):
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', file_name)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            datetime_str = f"{date_str} {time_str.replace('-', ':')}"
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        return datetime.min
    
    sorted_files = sorted(uploaded_files, key=extract_datetime, reverse=True)
    
    # 写回文件
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_files, f, ensure_ascii=False, indent=2)
    
    return True

def get_uploaded_files(json_file_path):
    """
    获取已上传文件列表
    
    Args:
        json_file_path (str): JSON文件路径
    
    Returns:
        set: 已上传文件名的集合
    """
    # 如果文件不存在，返回空集合
    if not os.path.exists(json_file_path):
        return set()
    
    # 读取文件内容
    with open(json_file_path, 'r', encoding='utf-8') as f:
        files = json.load(f)
    
    return set(files)

if __name__ == "__main__":
    # 测试代码
    json_file = ".uploaded_files.json"
    
    # 排序文件列表
    sorted_files = sort_uploaded_files_by_date(json_file)
    print(f"已排序 {len(sorted_files)} 个文件")
    
    # 显示前10个文件
    print("最新的10个文件:")
    for i, file in enumerate(sorted_files[:10]):
        print(f"{i+1}. {file}")