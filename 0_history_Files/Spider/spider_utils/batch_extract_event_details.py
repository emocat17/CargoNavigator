import os
import sys
import json
import re
from datetime import datetime

# 添加父目录到Python路径，确保能正确导入spider_utils模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 使用绝对导入
import spider_utils.uploaded_files_manager
is_file_uploaded = spider_utils.uploaded_files_manager.is_file_uploaded
get_uploaded_files = spider_utils.uploaded_files_manager.get_uploaded_files

def extract_direction_from_remark(remark):
    """尝试从备注中提取方向信息"""
    if not remark:
        return ""
    # 匹配 "XX往XX方向"
    match = re.search(r'([\u4e00-\u9fa5]+往[\u4e00-\u9fa5]+方向)', remark)
    if match:
        return match.group(1)
    return ""

def process_event_data(event):
    """
    处理单个事件数据，映射字段
    """
    highway_name = event.get("title", "未知高速")
    
    direction = event.get("directionname", "")
    if not direction:
        direction = extract_direction_from_remark(event.get("remark", ""))
    if not direction:
        direction = "未知方向"
        
    start_stake = event.get("startstake", "")
    end_stake = event.get("endstake", "")
    stake_number = f"{start_stake}-{end_stake}" if start_stake and end_stake else (start_stake or end_stake or "未知桩号")
    
    occtime = event.get("occtime", "")
    planovertime = event.get("planovertime")
    duration = f"{occtime}"
    if planovertime:
        duration += f" 至 {planovertime}"
    else:
        duration += " (预计结束时间未知)"
        
    # 获取最新进度
    latest_progress = ""
    tracks = event.get("track", [])
    if tracks:
        # 找到最后一个有内容的track
        for track in reversed(tracks):
            if track.get("content"):
                latest_progress = track.get("content")
                break
    
    if not latest_progress:
        latest_progress = event.get("remark", "暂无详情")
        
    publish_time = event.get("occtime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    url = f"https://www.fjetc.com/traffic-info/{event.get('eventid', '')}"
    
    return {
        "url": url,
        "highway_name": highway_name,
        "direction": direction,
        "stake_number": stake_number,
        "duration": duration,
        "latest_progress": latest_progress,
        "publish_time": publish_time,
        "extract_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_data": event # 保留原始数据以备查
    }

def save_to_markdown(data, filename):
    """
    将提取的数据保存为Markdown文件
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 福建高速交通事件详情\n\n")
            f.write(f"**URL**: {data['url']}\n\n")
            f.write(f"**发布时间**: {data['publish_time']}\n\n")
            
            f.write(f"## 高速名称\n\n{data['highway_name']}\n\n")
            f.write(f"## 方向\n\n{data['direction']}\n\n")
            f.write(f"## 桩号区间\n\n{data['stake_number']}\n\n")
            f.write(f"## 持续时间\n\n{data['duration']}\n\n")
            f.write(f"## 最新进度\n\n{data['latest_progress']}\n")
            
        print(f"数据已保存到 {filename}")
    except Exception as e:
        print(f"保存文件 {filename} 时出错: {e}")

def generate_filename(data):
    """
    根据发布时间、高速名称和桩号区间生成文件名
    """
    highway_name = data.get('highway_name', '未知高速')
    stake_number = data.get('stake_number', '未知桩号')
    
    if "未知" in highway_name or "未知" in stake_number:
        # 即使未知，也尝试生成文件名，避免丢数据，但原逻辑是跳过
        # 这里保留原逻辑的严格性，或者稍微放宽？
        # 原逻辑：return None
        return None
    
    publish_time = data.get('publish_time', '')
    if not publish_time:
        return None
    
    # 格式化发布时间
    date_part = publish_time.replace(' ', '_').replace(':', '-')
    
    # 移除特殊字符
    highway_name_clean = re.sub(r'[^\w\u4e00-\u9fff]', '_', highway_name)
    stake_number_clean = re.sub(r'[^\w\u4e00-\u9fff]', '_', stake_number)
    
    filename = f"{date_part}_{highway_name_clean}_{stake_number_clean}.md"
    return filename

def should_skip_file(filename, specific_dir, uploaded_files_set):
    """
    检查文件是否应该跳过
    """
    filepath = os.path.join(specific_dir, filename)
    if os.path.exists(filepath):
        return True, "文件已存在本地"
    
    if filename in uploaded_files_set:
        return True, "文件已上传到Dify"
    
    return False, ""

def process_event_json(json_file, uploaded_files_json=".uploaded_files.json"):
    """
    处理JSON文件中的事件数据
    """
    # 创建输出目录结构
    base_dir = os.path.join(parent_dir, "road_details")
    os.makedirs(base_dir, exist_ok=True)
    
    if "traffic" in json_file.lower():
        specific_dir = os.path.join(base_dir, "traffic_incident_details")
        collection_type = "交通事件"
    else:
        specific_dir = os.path.join(base_dir, "road_construction_details")
        collection_type = "道路施工"
    
    os.makedirs(specific_dir, exist_ok=True)
    
    # 查找JSON文件
    grandparent_dir = os.path.dirname(parent_dir)
    json_path = os.path.join(grandparent_dir, 'json', json_file) # ../Test/../json -> ../json ? No.
    # parent_dir is Test. grandparent_dir is Desktop. 
    # But json is in Test/json now (based on url_extract_api logic).
    # Wait, url_extract_api saved to Test/json.
    # So json_path should be os.path.join(parent_dir, 'json', json_file).
    
    json_path = os.path.join(parent_dir, 'json', json_file)
    if not os.path.exists(json_path):
        print(f"错误: 找不到JSON文件 {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            events_data = data.get('events_data', [])
    except Exception as e:
        print(f"读取JSON文件时出错: {e}")
        return
        
    if not events_data:
        print(f"JSON文件中没有找到事件详情数据 (events_data)")
        return

    # 加载已上传文件集合
    uploaded_files_set = get_uploaded_files(uploaded_files_json)
    
    print(f"开始处理 {len(events_data)} 个{collection_type}数据...")
    
    processed_count = 0
    filtered_count = 0
    skipped_count = 0
    
    for event in events_data:
        try:
            processed_data = process_event_data(event)
            filename = generate_filename(processed_data)
            
            if filename is None:
                filtered_count += 1
                continue
                
            should_skip, skip_reason = should_skip_file(filename, specific_dir, uploaded_files_set)
            if should_skip:
                skipped_count += 1
                # print(f"跳过: {filename} ({skip_reason})")
                continue
                
            filepath = os.path.join(specific_dir, filename)
            save_to_markdown(processed_data, filepath)
            processed_count += 1
            
        except Exception as e:
            print(f"处理事件时出错: {e}")
            
    print(f"{collection_type}处理完成: 成功 {processed_count}, 跳过 {skipped_count}, 过滤 {filtered_count}")

def main():
    uploaded_files_json = os.path.join(parent_dir, ".uploaded_files.json")
    
    process_event_json("Traffic_incident_code.json", uploaded_files_json)
    process_event_json("Road_construction_code.json", uploaded_files_json)

if __name__ == "__main__":
    main()
