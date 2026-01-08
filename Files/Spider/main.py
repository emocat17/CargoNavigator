import os
import sys
import subprocess
import time
from datetime import datetime, timedelta

# 添加当前目录到Python路径，确保能正确导入spider_utils模块
current_dir = os.path.dirname(os.path.abspath(__file__))
# 切换工作目录到脚本所在目录，确保相对路径正确
os.chdir(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 使用绝对导入
import spider_utils.uploaded_files_manager
sort_uploaded_files_by_date = spider_utils.uploaded_files_manager.sort_uploaded_files_by_date

# 本地已上传文件记录
UPLOADED_FILES_JSON = ".uploaded_files.json"

def run_python_script(script_path):
    """
    运行Python脚本并统计耗时
    
    Args:
        script_path (str): 脚本路径
        
    Returns:
        tuple: (是否成功运行, 耗时秒数)
    """
    print(f"\n{'='*50}")
    print(f"开始运行脚本: {script_path}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    start_time = time.time()
    
    try:
        # 使用subprocess运行脚本，不捕获输出，直接显示在终端
        result = subprocess.run([sys.executable, script_path], 
                              check=True, 
                              text=True)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"\n脚本 {script_path} 运行完成")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"耗时: {format_time(elapsed_time)}")
        
        return True, elapsed_time
        
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"运行脚本 {script_path} 时出错:")
        print(f"返回码: {e.returncode}")
        print(f"耗时: {format_time(elapsed_time)}")
        return False, elapsed_time
    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"运行脚本 {script_path} 时发生未知错误: {str(e)}")
        print(f"耗时: {format_time(elapsed_time)}")
        return False, elapsed_time

def format_time(seconds):
    """
    格式化时间显示
    
    Args:
        seconds (float): 秒数
        
    Returns:
        str: 格式化后的时间字符串
    """
    if seconds < 60:
        return f"{seconds:.2f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}分{remaining_seconds:.2f}秒"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}小时{remaining_minutes}分{remaining_seconds:.2f}秒"

def main():
    """主函数，按顺序运行脚本并统计总耗时"""
    print("开始执行福建高速交通信息爬取任务")
    print("此任务将按顺序执行以下步骤:")
    print("1. 提取交通事件和道路施工的URL链接")
    print("2. 批量提取事件详情并保存为Markdown文件")
    print("3. [可选] 上传文件到Dify知识库 (在代码中配置)")
    print(f"任务开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 记录总开始时间
    total_start_time = time.time()
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义要运行的脚本路径
    utils_dir = os.path.join(current_dir, "spider_utils")
    url_extract_script = os.path.join(utils_dir, "url_extract_api.py")
    batch_extract_script = os.path.join(utils_dir, "batch_extract_event_details.py")
    dify_upload_script = os.path.join(utils_dir, "Dify_folder_upload.py")
    
    # 检查脚本文件是否存在
    if not os.path.exists(url_extract_script):
        print(f"错误: 找不到脚本文件 {url_extract_script}")
        return
    
    if not os.path.exists(batch_extract_script):
        print(f"错误: 找不到脚本文件 {batch_extract_script}")
        return
    
    # 第一步：运行URL提取脚本
    print("\n第一步：提取交通事件和道路施工的URL链接")
    url_success, url_elapsed_time = run_python_script(url_extract_script)
    if not url_success:
        print("URL提取脚本运行失败，终止执行")
        return
    
    # 等待一段时间，确保前一个脚本完全完成并释放资源
    print("\n等待1秒，确保前一个脚本完全完成并释放资源...")
    time.sleep(1)
    
    # 强制垃圾回收，释放内存
    import gc
    gc.collect()
    
    # 第二步：运行批量事件详情提取脚本
    print("\n第二步：批量提取事件详情并保存为Markdown文件")
    batch_success, batch_elapsed_time = run_python_script(batch_extract_script)
    if not batch_success:
        print("批量事件详情提取脚本运行失败")
        return
    
    # 等待一段时间，确保前一个脚本完全完成并释放资源
    print("\n等待1秒，确保前一个脚本完全完成并释放资源...")
    time.sleep(1)
    
    # 强制垃圾回收，释放内存
    import gc
    gc.collect()
    
    # 第三步：上传文件到Dify知识库
    print("\n第三步：上传文件到Dify知识库")
    # 直接在代码中定义选择，1: 执行上传, 0: 跳过上传
    upload_choice = "1"  # 修改为"0"可跳过上传步骤
    
    dify_elapsed_time = 0
    dify_success = True
    
    if upload_choice == "1":
        # 检查Dify上传脚本是否存在
        if not os.path.exists(dify_upload_script):
            print(f"错误: 找不到脚本文件 {dify_upload_script}")
            dify_success = False
        else:
            # 运行Dify上传脚本
            dify_success, dify_elapsed_time = run_python_script(dify_upload_script)
    else:
        print("⏭️  跳过文件上传步骤 (upload_choice='0')")
    
    # 计算总耗时
    total_end_time = time.time()
    total_elapsed_time = total_end_time - total_start_time
    
    print("\n" + "="*50)
    print("✅ 所有任务已完成！")
    print("="*50)
    print(f"任务结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {format_time(total_elapsed_time)}")
    print("\n📊 各步骤耗时统计:")
    print(f"1. URL提取脚本: {format_time(url_elapsed_time)}")
    print(f"2. 批量详情提取脚本: {format_time(batch_elapsed_time)}")
    if upload_choice == "1":
        print(f"3. Dify文件上传脚本: {format_time(dify_elapsed_time)}")
        print(f"其他操作耗时: {format_time(total_elapsed_time - url_elapsed_time - batch_elapsed_time - dify_elapsed_time)}")
    else:
        print(f"其他操作耗时: {format_time(total_elapsed_time - url_elapsed_time - batch_elapsed_time)}")
    
    # 最终垃圾回收
    import gc
    gc.collect()
    print("已完成最终垃圾回收，释放所有可用资源")
    
    # 自动排序上传记录
    print("\n" + "="*50)
    print("正在自动排序上传记录...")
    try:
        sort_uploaded_files_by_date(UPLOADED_FILES_JSON)
        print("✅ 上传记录已按日期排序（最新在前）")
    except Exception as e:
        print(f"❌ 排序上传记录时出错: {str(e)}")
    print("="*50)


if __name__ == "__main__":
    main()