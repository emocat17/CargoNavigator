import asyncio
import json
import os
from datetime import datetime
from crawl4ai import AsyncWebCrawler, JsonCssExtractionStrategy, CrawlerRunConfig

async def extract_event_details(url):
    """
    提取单个事件详情页面的信息
    
    Args:
        url (str): 事件详情页面URL
        
    Returns:
        dict: 包含提取信息的字典
    """
    # 定义提取策略
    schema = {
        "name": "Event Details",
        "baseSelector": "#app",
        "fields": [
            {
                "name": "highway_name",
                "selector": ".font-bold.text-zinc-900.text-xl",
                "type": "text"
            },
            {
                "name": "direction",
                "selector": ".table-row:nth-child(1) .table-value",
                "type": "text"
            },
            {
                "name": "stake_number",
                "selector": ".table-row:nth-child(2) .table-value",
                "type": "text"
            },
            {
                "name": "duration",
                "selector": ".table-row:nth-child(3) .table-value",
                "type": "text"
            },
            {
                "name": "latest_progress",
                "selector": ".el-timeline-item__content p",
                "type": "text"
            },
            {
                "name": "publish_time",
                "selector": "#app > div > div > div.flex-grow > div > div.bg-white.px-4.pb-2.pt-4.md\\:px-10.md\\:pt-4 > div.flex.flex-col.md\\:flex-row.p-4.gap-4.md\\:gap-16 > div.md\\:basis-1\\/3.flex-shrink-0 > ul > li > div.el-timeline-item__wrapper > div.el-timeline-item__timestamp.is-top",
                "type": "text"
            }
        ]
    }
    
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)
    
    # 配置爬虫，等待JavaScript执行完成
    config = CrawlerRunConfig(
        wait_until="networkidle",
        verbose=True,
        extraction_strategy=extraction_strategy
    )
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url, config=config)
        
        # 保存HTML源码以便分析
        event_code = url.split('/')[-1]
        html_filename = f"page_source_{event_code}.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(result.html)
        print(f"页面源码已保存到 {html_filename}")
        
        if result.success:
            print(f"提取成功，extracted_content类型: {type(result.extracted_content)}")
            print(f"提取内容: {result.extracted_content}")
            
            if result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)
                    if extracted_data and len(extracted_data) > 0:
                        data = extracted_data[0]
                        return {
                            "url": url,
                            "highway_name": data.get("highway_name", "未找到高速名称"),
                            "direction": data.get("direction", "未找到方向信息"),
                            "stake_number": data.get("stake_number", "未找到桩号区间"),
                            "duration": data.get("duration", "未找到持续时间"),
                            "latest_progress": data.get("latest_progress", "未找到最新进度"),
                            "publish_time": data.get("publish_time", "未找到发布时间")
                        }
                    else:
                        return {
                            "url": url,
                            "error": "未提取到内容",
                            "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                except json.JSONDecodeError as e:
                    return {
                            "url": url,
                            "error": f"无法解析提取的数据: {e}",
                            "raw_content": result.extracted_content,
                            "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
            else:
                # 尝试使用BeautifulSoup解析HTML
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.html, 'html.parser')
                    
                    # 尝试使用更简单的选择器
                    # 1. 首先尝试找到包含事件详情的主要区域
                    main_content = soup.select_one('.bg-white')
                    print(f"找到主要内容区域: {main_content is not None}")
                    
                    # 2. 尝试提取高速名称 - 查找包含粗体文本的元素
                    highway_name_elem = soup.select_one('.font-bold.text-xl')
                    highway_name = highway_name_elem.get_text(strip=True) if highway_name_elem else "未找到高速名称"
                    print(f"高速名称: {highway_name}")
                    
                    # 3. 尝试提取表格数据 - 查找所有table-value类的元素
                    table_values = soup.select('.table-value')
                    print(f"找到 {len(table_values)} 个表格值")
                    
                    direction = table_values[0].get_text(strip=True) if len(table_values) > 0 else "未找到方向信息"
                    stake_number = table_values[1].get_text(strip=True) if len(table_values) > 1 else "未找到桩号区间"
                    duration = table_values[2].get_text(strip=True) if len(table_values) > 2 else "未找到持续时间"
                    
                    print(f"方向: {direction}")
                    print(f"桩号区间: {stake_number}")
                    print(f"持续时间: {duration}")
                    
                    # 4. 尝试提取最新进度 - 查找时间线内容
                    timeline_content = soup.select_one('.el-timeline-item__content p')
                    latest_progress = timeline_content.get_text(strip=True) if timeline_content else "未找到最新进度"
                    print(f"最新进度: {latest_progress}")
                    
                    return {
                            "url": url,
                            "highway_name": highway_name,
                            "direction": direction,
                            "stake_number": stake_number,
                            "duration": duration,
                            "latest_progress": latest_progress,
                            "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                except Exception as e:
                    return {
                            "url": url,
                            "error": f"BeautifulSoup解析失败: {e}",
                            "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
        else:
            return {
                "url": url,
                "error": f"无法获取页面内容: {result.error_message}",
                "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

def save_to_md(data, filename):
    """
    将提取的数据保存为Markdown文件
    
    Args:
        data (dict): 包含提取信息的字典
        filename (str): 保存的文件名
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# 福建高速交通事件详情\n\n")
        f.write(f"**URL**: {data['url']}\n\n")
        f.write(f"**发布时间**: {data['publish_time']}\n\n")
        
        if "error" in data:
            f.write(f"**错误**: {data['error']}\n")
        else:
            f.write(f"## 高速名称\n\n{data['highway_name']}\n\n")
            f.write(f"## 方向\n\n{data['direction']}\n\n")
            f.write(f"## 桩号区间\n\n{data['stake_number']}\n\n")
            f.write(f"## 持续时间\n\n{data['duration']}\n\n")
            f.write(f"## 最新进度\n\n{data['latest_progress']}\n")
    
    print(f"数据已保存到 {filename}")

def generate_filename(data):
    """
    根据发布时间和高速名称生成文件名
    
    Args:
        data (dict): 提取的数据
        
    Returns:
        str: 生成的文件名
    """
    # 从发布时间中提取日期部分，替换冒号和空格
    publish_time = data.get('publish_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    date_part = publish_time.split(' ')[0]  # 获取日期部分
    
    # 获取高速名称，移除特殊字符
    highway_name = data.get('highway_name', '未知高速')
    # 移除特殊字符，只保留中文、字母、数字和下划线
    import re
    highway_name_clean = re.sub(r'[^\w\u4e00-\u9fff]', '_', highway_name)
    
    # 生成文件名
    filename = f"{date_part}_{highway_name_clean}.md"
    return filename

async def main():
    """主函数，提取单个事件详情"""
    url = "https://www.fjetc.com/traffic-info/1759736843055771"
    print(f"正在提取URL: {url}")
    
    # 提取事件详情
    event_details = await extract_event_details(url)
    
    # 生成文件名
    filename = generate_filename(event_details)
    
    # 保存为Markdown文件
    save_to_md(event_details, filename)
    
    print("\n提取结果:")
    print(json.dumps(event_details, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())