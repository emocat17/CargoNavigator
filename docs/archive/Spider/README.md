# 福建高速交通信息爬虫系统技术文档

## 系统概述

福建高速交通信息爬虫系统是一个专门用于抓取福建省高速公路交通事件和道路施工信息的自动化数据采集系统。该系统通过调用官网API接口获取实时交通数据，并直接解析返回的JSON数据生成结构化文档，最后上传到知识库系统，为交通管理和决策提供数据支持。

## 技术栈

- **编程语言**: Python 3.8+
- **API 请求**: requests (配合 AES 加解密)
- **数据处理**: json, re, datetime
- **加密处理**: pycryptodome (AES CBC模式)
- **文件操作**: os, sys
- **知识库集成**: Dify API

## 系统架构

### 核心模块

1. **主控制模块** (`main.py`)
   - 系统执行流程控制
   - 子进程管理与资源监控
   - 任务耗时统计与性能分析
   - 自动垃圾回收与内存管理

2. **URL提取模块** (`spider_utils/url_extract_api.py`)
   - 通过 API 获取交通事件和道路施工数据
   - 处理 AES 加密请求参数和解密响应数据
   - 保存包含完整事件详情的 JSON 数据

3. **事件详情处理模块** (`spider_utils/batch_extract_event_details.py`)
   - 直接解析 API 返回的 JSON 数据
   - 提取字段：高速名称、方向、桩号区间、持续时间、最新进度、发布时间
   - 数据清洗与格式化
   - 生成 Markdown 格式文件

4. **文件上传模块** (`spider_utils/Dify_folder_upload.py`)
   - 批量文件上传到知识库
   - 分批次处理与索引等待
   - 上传状态监控与结果统计

5. **上传管理模块** (`spider_utils/uploaded_files_manager.py`)
   - 上传记录管理
   - 文件去重检查
   - 按日期排序功能

## 系统工作流程

### 第一阶段：数据获取 (API 方式)

1. **构造加密请求**
   - 使用 AES CBC 模式加密查询参数
   - 设置请求头 (Referer, Origin, User-Agent)

2. **调用 API 接口**
   - 访问 `https://www.fjetc.com/mgsfwq/FunctionList/Traffic/getTrafficMessage`
   - 获取加密的响应数据

3. **解密与保存**
   - 解密响应内容
   - 将完整的 JSON 数据（包含 `events_data`）保存到 `json/` 目录

### 第二阶段：数据解析与生成

1. **读取 JSON 数据**
   - 读取第一阶段保存的 `Traffic_incident_code.json` 和 `Road_construction_code.json`

2. **数据映射**
   - 遍历 `events_data` 列表
   - 提取并组合关键字段（如拼接起止桩号、提取方向信息）
   - 构造 Markdown 内容

3. **数据筛选与保存**
   - 过滤包含"未知"关键信息的数据（可选）
   - 检查文件是否已存在或已上传
   - 生成唯一文件名并保存到 `road_details/` 目录

### 第三阶段：知识库上传

1. **检查与排序**
   - 检查目标文件夹是否存在
   - 自动对上传记录进行按日期排序

2. **批量上传**
   - 读取 `road_details` 目录下的 Markdown 文件
   - 调用 Dify API 上传文件
   - 支持分批上传和等待索引完成

3. **记录更新**
   - 更新本地 `.uploaded_files.json` 记录
   - 确保不重复上传已存在的文件

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **运行爬虫**
   ```bash
   python main.py
   ```

3. **查看结果**
   - 控制台实时显示各阶段进度和耗时
   - 生成的 Markdown 文件位于 `road_details/` 目录
   - 上传记录保存在 `.uploaded_files.json`
