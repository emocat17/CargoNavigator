import os
import sys
import json
import time
import requests
from datetime import datetime

# 添加父目录到Python路径，确保能正确导入spider_utils模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 使用绝对导入
import spider_utils.uploaded_files_manager
is_file_uploaded = spider_utils.uploaded_files_manager.is_file_uploaded
get_uploaded_files_from_json = spider_utils.uploaded_files_manager.get_uploaded_files
sort_uploaded_files_by_date = spider_utils.uploaded_files_manager.sort_uploaded_files_by_date
add_uploaded_file = spider_utils.uploaded_files_manager.add_uploaded_file
 
# 配置信息
API_KEY = "dataset-dUYmEaIBWW8BnkXJ1ZHkra73"  # ⚠️ 请替换为您的实际API密钥！
API_URL = "http://10.24.23.17:80/v1"  # API地址已配置
 
# 代理配置 - Clash代理
USE_PROXY = False  # 设置为False可禁用代理
PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
} if USE_PROXY else None # 如果是使用Dify官方在线的服务需要使用代理；
 
 
def get_dataset_info(dataset_id):
    """
    获取数据集信息
    
    Args:
        dataset_id (str): 数据集ID
    
    Returns:
        dict: 数据集信息
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    
    url = f"{API_URL}/datasets/{dataset_id}"
    
    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=PROXIES,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取数据集信息失败！状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 获取数据集信息出错: {e}")
        return None


def get_uploaded_files_from_api(dataset_id):
    """
    从API获取已上传的文件列表
    
    Args:
        dataset_id (str): 数据集ID
    
    Returns:
        set: 已上传文件名的集合
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    
    url = f"{API_URL}/datasets/{dataset_id}/documents"
    
    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=PROXIES,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            documents = data.get('data', [])
            
            # 提取文件名
            uploaded_files = set()
            for doc in documents:
                # 使用name作为文件名
                file_name = doc.get('name', '')
                if file_name:
                    uploaded_files.add(file_name)
            
            return uploaded_files
        else:
            print(f"❌ 获取已上传文件列表失败！状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return set()
    except Exception as e:
        print(f"❌ 获取已上传文件列表出错: {e}")
        return set()


def get_uploaded_files(dataset_id, uploaded_files_json=".uploaded_files.json"):
    """
    获取已上传的文件列表（从本地记录和API）
    
    Args:
        dataset_id (str): 数据集ID
        uploaded_files_json (str): 本地已上传文件记录路径
    
    Returns:
        set: 已上传文件名的集合
    """
    # 从本地记录获取
    local_uploaded = get_uploaded_files_from_json(uploaded_files_json)
    
    # 从API获取
    api_uploaded = get_uploaded_files_from_api(dataset_id)
    
    # 合并两个集合
    return local_uploaded.union(api_uploaded)


def create_by_file(dataset_id, file_path=None, silent=False, uploaded_files_json=".uploaded_files.json"):
    """
    通过文件上传创建知识库文档
    
    Args:
        dataset_id (str): 数据集ID
        file_path (str): 文件路径，如果为None则使用默认路径
        silent (bool): 是否静默模式，减少输出信息
        uploaded_files_json (str): 本地已上传文件记录路径
    
    Returns:
        dict: 上传结果
    """
    # 默认文件路径
    if file_path is None:
        file_path = "d://test.pdf"  # 替换为你要上传的文件路径
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        if not silent:
            print(f"错误：文件不存在 - {file_path}")
        return None
    
    # 获取文件名
    file_name = os.path.basename(file_path)
    
    # 检查文件是否已上传（从本地记录）
    if is_file_uploaded(uploaded_files_json, file_name):
        if not silent:
            print(f"⏭️  文件已存在于上传记录中，跳过: {file_name}")
        return {"status": "skipped", "message": "文件已存在于上传记录中"}
    
    # 获取数据集信息，以确定文档格式
    if not silent:
        print("🔍 获取数据集信息...")
    dataset_info = get_dataset_info(dataset_id)
    
    # 获取文件名和确定文件类型（提前获取以便在doc_form判断中使用）
    file_name = os.path.basename(file_path)
    file_extension = os.path.splitext(file_name)[1].lower()
    
    if not dataset_info:
        if not silent:
            print("❌ 无法获取数据集信息，使用默认文档格式")
        doc_form = "text_model"  # 默认使用文本模型
    else:
        if not silent:
            # 只打印关键数据集信息
            print(f"📊 数据集名称: {dataset_info.get('name', '未知')}")
            print(f"📊 数据集描述: {dataset_info.get('description', '无')}")
            print(f"📊 文档数量: {dataset_info.get('document_count', 0)}")
        
        # 从数据集信息中获取文档格式
        indexing_technique = dataset_info.get("indexing_technique", "")
        
        # 尝试获取数据集的文档格式
        # 如果数据集有指定doc_form，则使用它；否则根据文件类型决定
        dataset_doc_form = dataset_info.get("doc_form", None)
        if dataset_doc_form:
            doc_form = dataset_doc_form
        else:
            # 根据文件扩展名确定文档格式
            if file_extension in ['.txt', '.md']:
                doc_form = "text_model"
            else:
                doc_form = "pdf_model"
    
    # 请求头
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    
    # 获取文件名和确定文件类型
    file_name = os.path.basename(file_path)
    file_extension = os.path.splitext(file_name)[1].lower()
    
    # 根据文件扩展名确定MIME类型
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.md': 'text/markdown'
    }
    
    content_type = mime_types.get(file_extension, 'application/octet-stream')
    
    try:
        # 请求体（文件上传）
        with open(file_path, "rb") as file:
            files = {
                "file": (file_name, file, content_type)
            }
            
            # 数据配置
            data = {
                "indexing_technique": "high_quality",
                "process_rule": {
                    "rules": {
                        "pre_processing_rules": [
                            {
                                "id": "remove_extra_spaces",
                                "enabled": True
                            },
                            {
                                "id": "remove_urls_emails", 
                                "enabled": True
                            }
                        ],
                        "segmentation": {
                            "separator": "###",
                            "max_tokens": 1000
                        }
                    },
                    "mode": "automatic"
                },
                # 添加文档格式参数
                "doc_form": doc_form
            }
            
            form_data = {
                "data": json.dumps(data)
            }
            
            # 发送请求 - 修复URL中的连字符为下划线，并使用传入的dataset_id
            url = f"{API_URL}/datasets/{dataset_id}/document/create_by_file"
            
            response = requests.post(
                url,
                headers=headers,
                data=form_data,
                files=files,
                proxies=PROXIES,  # 使用Clash代理
                timeout=300  # 5分钟超时
            )
            
            # 处理响应
            if response.status_code == 200:
                if not silent:
                    print(f"✅ {file_name} 上传成功！")
                result = response.json()
                
                # 将文件添加到本地上传记录
                if add_uploaded_file(uploaded_files_json, file_name):
                    if not silent:
                        print(f"📝 已将 {file_name} 添加到上传记录")
                
                return result
            else:
                if not silent:
                    print(f"❌ {file_name} 上传失败！状态码: {response.status_code}")
                return None
                
    except FileNotFoundError:
        if not silent:
            print(f"❌ 错误：找不到文件 - {file_path}")
        return None
    except requests.exceptions.Timeout:
        if not silent:
            print("❌ 错误：请求超时")
        return None
    except requests.exceptions.RequestException as e:
        if not silent:
            print(f"❌ 请求错误: {e}")
        return None
    except Exception as e:
        if not silent:
            print(f"❌ 未知错误: {e}")
        return None


def upload_folder_files(dataset_id, folder_path, uploaded_files=None, batch_size=20, wait_for_indexing=False, uploaded_files_json=".uploaded_files.json"):
    """
    上传指定文件夹下的所有文件，排除已上传的文件，支持分批次上传
    
    Args:
        dataset_id (str): 数据集ID
        folder_path (str): 文件夹路径
        uploaded_files (set): 已上传文件名的集合
        batch_size (int): 每批次上传的文件数量，默认为20
        wait_for_indexing (bool): 是否等待每批次文件索引完成后再继续下一批次
        uploaded_files_json (str): 本地已上传文件记录路径
    
    Returns:
        tuple: (上传结果列表, 新上传的文件集合)
    """
    results = []
    new_uploaded_files = set() if uploaded_files is None else uploaded_files.copy()
    
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"❌ 错误：文件夹不存在 - {folder_path}")
        return results, new_uploaded_files
    
    if not os.path.isdir(folder_path):
        print(f"❌ 错误：路径不是文件夹 - {folder_path}")
        return results, new_uploaded_files
    
    # 获取文件夹下所有文件
    all_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            # 使用文件名作为唯一标识
            all_files.append((file_path, file))
    
    # 过滤出未上传的文件
    files_to_upload = []
    for file_path, file_name in all_files:
        if file_name not in new_uploaded_files:
            files_to_upload.append((file_path, file_name))
    
    if not files_to_upload:
        print(f"❌ 文件夹中没有找到未上传的文件 - {folder_path}")
        return results, new_uploaded_files
    
    print(f"📁 找到 {len(all_files)} 个文件，其中 {len(files_to_upload)} 个未上传，开始分批次上传...")
    print(f"📊 每批次上传 {batch_size} 个文件，共需 {len(files_to_upload) // batch_size + (1 if len(files_to_upload) % batch_size > 0 else 0)} 批次")
    
    # 分批次上传文件
    total_batches = len(files_to_upload) // batch_size + (1 if len(files_to_upload) % batch_size > 0 else 0)
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(files_to_upload))
        batch_files = files_to_upload[start_idx:end_idx]
        
        print(f"\n📦 正在上传第 {batch_idx + 1}/{total_batches} 批次，包含 {len(batch_files)} 个文件...")
        
        batch_results = []
        batch_document_ids = []  # 存储当前批次上传成功的文档ID
        
        for file_path, file_name in batch_files:
            result = create_by_file(dataset_id, file_path, silent=True, uploaded_files_json=uploaded_files_json)
            
            # 如果上传成功，将文件名添加到已上传集合
            if result is not None:
                new_uploaded_files.add(file_name)
                # 获取文档ID
                doc_id = result['document']['id']
                batch_document_ids.append(doc_id)
            
            batch_results.append({
                'file_path': file_path,
                'file_name': file_name,
                'result': result,
                'success': result is not None
            })
        
        # 统计当前批次结果
        batch_success_count = sum(1 for r in batch_results if r['success'])
        print(f"📊 第 {batch_idx + 1} 批次结果: 成功 {batch_success_count} / {len(batch_results)}")
        
        # 显示当前批次成功上传的文件
        if batch_success_count > 0:
            print("✅ 本批次成功上传的文件:")
            for r in batch_results:
                if r['success']:
                    doc_id = r['result']['document']['id']
                    print(f"  - {r['file_name']} (ID: {doc_id})")
        
        # 显示当前批次失败的文件
        if batch_success_count < len(batch_results):
            print("❌ 本批次上传失败的文件:")
            for r in batch_results:
                if not r['success']:
                    print(f"  - {r['file_name']}")
        
        # 如果需要等待索引完成
        if wait_for_indexing and batch_document_ids:
            print(f"\n⏳ 等待本批次 {len(batch_document_ids)} 个文档索引完成...")
            
            # 等待所有文档索引完成
            all_indexed = True
            for doc_id in batch_document_ids:
                if not wait_for_document_indexing(dataset_id, doc_id, max_wait_time=180, check_interval=10):
                    all_indexed = False
            
            if all_indexed:
                print("✅ 本批次所有文档索引完成！")
            else:
                print("⚠️ 本批次部分文档索引失败或超时")
        
        # 将批次结果添加到总结果
        results.extend(batch_results)
        
        # 如果不是最后一批，等待一段时间再继续
        if batch_idx < total_batches - 1:
            wait_time = 5 if wait_for_indexing else 5
            print(f"⏳ 等待{wait_time}秒后继续下一批次...")
            time.sleep(wait_time)
    
    # 统计总体结果
    total_success_count = sum(1 for r in results if r['success'])
    print(f"\n📊 总体上传结果: 成功 {total_success_count} / {len(results)}")
    
    return results, new_uploaded_files


def main():
    # 配置参数
    dataset_id = "ad8b004c-df9a-4eba-90b7-2a1aa6a811f6"  # 您的数据集ID
    # 使用绝对路径
    folder_path = os.path.join(parent_dir, "road_details")
    uploaded_files_json = os.path.join(parent_dir, ".uploaded_files.json")
    
    print(f"🚀 开始执行上传脚本...")
    print(f"📂 目标文件夹: {folder_path}")
    print(f"🆔 数据集ID: {dataset_id}")
    
    # 先对上传记录进行排序
    print(f"🔄 正在排序上传记录...")
    sort_uploaded_files_by_date(uploaded_files_json)
    print(f"✅ 上传记录已按日期排序（最新在前）")
    
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"❌ 错误：文件夹不存在 - {folder_path}")
        sys.exit(1)
    
    # 检查数据集信息
    print(f"🔍 正在获取数据集信息...")
    dataset_info = get_dataset_info(dataset_id)
    
    if dataset_info:
        print(f"✅ 成功获取数据集信息: {dataset_info.get('name', '未知')}")
        print("\n" + "=" * 50)
        print("📁 开始上传文件夹中的文件...")
        print("=" * 50)
        
        # 获取已上传文件列表
        print(f"🔍 正在获取已上传文件列表...")
        uploaded_files = get_uploaded_files(dataset_info['id'], uploaded_files_json)
        print(f"📋 已上传文件数量: {len(uploaded_files)}")
        
        # 上传文件夹中的文件，使用分批次上传，每批次最多20个文件，并等待索引完成
        results, new_uploaded_files = upload_folder_files(
            dataset_info['id'], 
            folder_path, 
            uploaded_files, 
            batch_size=20,
            wait_for_indexing=True,  # 启用等待索引完成
            uploaded_files_json=uploaded_files_json  # 传递上传记录文件路径
        )
        
        # 显示上传结果
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - success_count
        
        print("\n" + "=" * 50)
        print("📊 上传结果汇总:")
        print(f"✅ 成功上传: {success_count} 个文件")
        print(f"❌ 上传失败: {fail_count} 个文件")
        print("=" * 50)
        
        if fail_count > 0:
            print("\n❌ 上传失败的文件:")
            for result in results:
                if not result['success']:
                    print(f"  - {result['file_name']}")
    else:
        print("❌ 无法获取数据集信息，请检查API配置")


def check_document_status(dataset_id, document_id):
    """
    检查文档上传状态和索引状态
    
    Args:
        dataset_id (str): 数据集ID
        document_id (str): 文档ID
    
    Returns:
        dict: 文档状态信息
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    
    url = f"{API_URL}/datasets/{dataset_id}/documents/{document_id}"
    
    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=PROXIES,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取文档状态失败！状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 获取文档状态出错: {e}")
        return None


def wait_for_document_indexing(dataset_id, document_id, max_wait_time=300, check_interval=10):
    """
    等待文档索引完成
    
    Args:
        dataset_id (str): 数据集ID
        document_id (str): 文档ID
        max_wait_time (int): 最大等待时间（秒），默认5分钟
        check_interval (int): 检查间隔（秒），默认10秒
    
    Returns:
        bool: 是否索引成功完成
    """
    print(f"⏳ 等待文档 {document_id} 索引完成...")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        doc_status = check_document_status(dataset_id, document_id)
        
        if doc_status:
            indexing_status = doc_status.get('indexing_status', '')
            display_status = doc_status.get('display_status', '')
            
            print(f"📊 文档状态: {display_status} (索引状态: {indexing_status})")
            
            if indexing_status == 'completed':
                print(f"✅ 文档 {document_id} 索引完成！")
                return True
            elif indexing_status == 'error':
                error = doc_status.get('error', '未知错误')
                print(f"❌ 文档 {document_id} 索引失败: {error}")
                return False
            elif indexing_status == 'paused':
                print(f"⚠️ 文档 {document_id} 索引已暂停")
                return False
        
        time.sleep(check_interval)
    
    print(f"⏰ 等待文档 {document_id} 索引超时")
    return False


if __name__ == "__main__":
    main()