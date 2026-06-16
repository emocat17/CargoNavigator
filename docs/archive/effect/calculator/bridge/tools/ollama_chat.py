import requests
import re
import json

# Ollama配置
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:8b"

# 系统提示词
system_prompt = """
你是一个路径信息提取专家。你的任务是从一段冗长的导航指令中，按照顺序提取出所有关键的路径节点，并生成一个用 `--` 连接的单一字符串。

你将收到一个包含 `start_junction`、`end_junction` 和 `instruction` 三个键的JSON对象。`start_junction` 是起点，`end_junction` 是终点，`instruction` 是从起点到终点的详细驾驶指令。

**请严格遵守以下提取规则：**

1.  **提取范围**：你需要从 `start_junction` 和 `end_junction` 中提取起点和终点名称。

2. **提取范围**：你需要从 `instruction` 文本中提取以下所有类型的节点：
    *   高速公路名称
    *   枢纽、互通（如 天宝枢纽, 南靖互通）
    *   收费站
    *   具名桥梁
    *   具名隧道
    *   连接道路（如 S61漳州北连接线, 漳华路）

3.  **提取顺序**：
    *   首先输出起点名称
    *   然后按照节点在 `instruction` 文本中出现的先后顺序进行提取和排列
    *   最后输出终点名称

4.  **节点概括**：
    *   如果一系列连续的桥梁或隧道有共同的前缀（例如"XXX2号桥、XXX1号桥"），将它们概括为一个节点（例如"XXX大桥"）。
    *   如果道路的名称中连续包含同一个地面的多个路段,请将节点名称简化为XXX（比如董坪1号大桥左桥--董坪2号大桥左桥--董坪4号中桥--董坪5号中桥，可以简化成董坪大桥）

5.  **信息过滤**：必须忽略以下信息：
    *   所有距离数字（如"1.5千米"、"894米"）。
    *   所有方向词（如"向东南"、"向东"、"靠左"）。
    *   所有常规驾驶动作（如"直行进入隧道"、"向右前方行驶进入匝道"、"左转调头"）。
    *   重复提及的道路名称（如"途径G76厦蓉高速"）。

6.  **输出格式**：最终输出只包含一个由 `--` 连接的字符串，不要包含任何解释、JSON格式或markdown代码块。
请根据以上规则，处理我接下来提供的数据。
"""

def extract_path_string(path_data):
    """
    从路径数据中提取路径字符串
    
    参数:
        path_data (dict): 包含start_junction、end_junction和instruction的字典
        
    返回:
        str: 提取的路径字符串，由'--'连接
    """
    messages=[
        {
            "role": "system", 
            "content": system_prompt
        },
        {
            "role": "assistant", 
            "content": "好的，我明白了。我将严格按照您的规则，从导航指令中按顺序提取所有关键节点，并生成指定格式的字符串。请提供数据。"
        },
        {
            "role": "user", 
            "content": f"{path_data}"
        }
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "temperature": 0.3
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # 获取模型返回的原始内容
        raw_content = result.get("message", {}).get("content", "")
        
        # 使用正则表达式提取最终的路径字符串
        # 查找由 "--" 连接的字符串，排除思考过程
        pattern = r'^(.*?)--(.*?)--(.*?)--(.*?)--(.*?)$'
        match = re.search(pattern, raw_content, re.MULTILINE)

        if match:
            # 如果找到匹配的路径字符串，直接输出
            path_string_details = match.group(0)
            return path_string_details
        else:
            # 如果没有找到标准格式，尝试提取第一行非思考过程的内容
            lines = raw_content.split('\n')
            for line in lines:
                line = line.strip()
                # 跳过思考过程相关的行
                if line and not line.startswith('好的，我现在需要处理') and not line.startswith('首先') and not line.startswith('接下来') and not line.startswith('然后') and not line.startswith('最后') and not line.startswith('Sure') and not line.startswith('Here'):
                     # 简单的验证，至少包含一个 -- 
                    if '--' in line:
                        return line
            
            # 如果还是找不到，返回原始内容的第一行非空行
            for line in lines:
                if line.strip():
                    return line.strip()
                    
            return None
            
    except Exception as e:
        print(f"调用Ollama API时出错: {str(e)}")
        return None

if __name__ == "__main__":
    # 测试代码
    example_path_data = {
        "start_junction": "测试起点",
        "end_junction": "测试终点",
        "instruction": "向南行驶26米左转；沿测试路向东行驶1.1千米；途径测试大桥向北行驶。"
    }
    print(extract_path_string(example_path_data))
