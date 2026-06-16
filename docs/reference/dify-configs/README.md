# Dify API 测试工具

本目录包含用于测试Dify API的Python脚本。

## 文件说明

1. **simple_chat.py** - 简单的交互式对话工具，包含预设测试问题，会自动识别问题分类，然后调用对应工具进行回复；
   - 填写交通运输申请表信息问题
   - 给出完整的路线规划，用于查询高速路况和天气等通行建议/路线评价

## 使用方法
直接嵌入：
```html
    <iframe
        src="http://103.40.13.100:23452/chatbot/lAJABZGNSYc58Blm"
        style="width: 100%; height: 100%; min-height: 700px"
        frameborder="0"
        allow="microphone">
    </iframe>
```
### 交互式对话

```bash
cd D:/SourceTree/front/Files/Dify_Database
python simple_chat.py
```

脚本启动后会自动运行预设测试问题："如何确定自己的运输车辆型号？有没有示意图？"

然后进入交互式对话模式，您可以：
- 输入您的问题，系统会调用Dify API并返回回答
- 输入 'test' 重复运行预设测试问题
- 输入 'quit' 退出对话

## API配置

- **API端点**: `http://103.40.13.100:23452/v1/chat-messages`
- **API密钥**: `app-Nj039we0kvOtsQFWW8vZX6Sd`

## 预设测试问题

"如何确定自己的运输车辆型号？有没有示意图？"

该问题会返回关于确定运输车辆型号的方法和常见大件运输车辆类型示意图的详细信息。

## 注意事项

1. 确保网络连接正常，可以访问API端点
2. 对话ID会在多轮对话中自动更新，以保持对话上下文
3. 脚本使用阻塞模式（blocking mode）获取响应

## 自定义使用

您可以根据需要修改脚本中的以下内容：

- API密钥
- API端点
- 用户ID
- 预设测试问题
- 响应模式（blocking/streaming）

## 故障排除

如果遇到问题，请检查：

1. 网络连接是否正常
2. API密钥是否正确
3. API端点是否可访问
4. Python环境是否安装了requests库

如果没有安装requests库，可以使用以下命令安装：

```bash
pip install requests
```



# 申请书填写回复客服
   大模型识别后，和正常大模型一样进行回复；

# 路线评价回复：
方便调用和前段使用，返回json格式数据；比如：
问题：(可自然语言)
```markdown
10月10日出发，
test_data = {
"start_junction": "北村",
"end_junction": "海沧",
"loads_ton": [10, 15, 12],
"spacings": [3.5, 1.2],
"max_path_length": None,
"top_n": 3
}

长6宽3高4，重39吨；三条路线如下：

"北村-G76-天宝-G76-陈巷-G76-海沧",
"北村-G25-畔溪-G1517-港后-G15-海沧",
"北村-G25-畔溪-G25-跃村-G70-前塘-S11-庄前-S53-渔溪-G15-港后-G15-海沧",
```

回复：
```json
{
    "route_id": "route_1",
    "route_name": "北村-G76-天宝-G76-陈巷-G76-海沧",
    "overall_assessment": {
        "recommendation": "推荐",
        "risk_level": "低",
        "score": 7.2,
        "key_factors": [
            "桥梁安全系数较高",
            "施工影响最小",
            "通行时间最短"
        ]
    },
    "traffic_analysis": {
        "estimated_time": "约3小时15分钟",
        "construction_impacts": [
            {
                "location": "G76厦蓉高速龙岩段K114-K115处",
                "impact_level": "中等",
                "lane_occupancy": "主车道、应急车道",
                "delay_minutes": 15
            }
        ],
        "traffic_incidents": [

        ],
        "total_delay": 15,
        "recommended_time_window": "上午8:00-11:00（避开施工高峰期）"
    },
    "route_compatibility": {
        "dimension_check": {
            "height_limit": 0,
            "vehicle_height": 4,
            "height_status": "通过 6/6 个检查点",
            "weight_limit": 0,
            "vehicle_weight": 39,
            "weight_status": "符合 6/6 个路段要求"
        },
        "structural_safety": {
            "total_bridges": 8,
            "high_risk_bridges": 0,
            "min_effect_ratio": 0.65,
            "max_moment_ratio": 0.78,
            "safety_threshold": 0.8,
            "safety_assessment": "安全通行"
        },
        "compliance_status": "完全符合"
    },
    "recommendations": {
        "for_user": [
            "通过施工路段时保持安全车距",
            "控制车速在60km/h以下",
            "避开施工高峰期"
        ],
        "for_approver": {
            "approval_decision": "建议批准",
            "special_conditions": [
                "通过施工路段时需减速慢行",
                "出发前关注天气预报"
            ],
            "risk_notes": "路线相对直接，桥梁安全系数较高，风险可控"
        }
    },
    "metadata": {
        "assessment_date": "2025年10月9日",
        "data_sources": [
            "福建省高速公路数据库",
            "施工信息库",
            "高德地图MCP"
        ],
        "confidence_level": "高"
    }
}
```