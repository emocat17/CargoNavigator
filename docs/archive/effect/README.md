# 桥梁效应计算系统技术说明文档

## 1. 系统概述

桥梁效应计算系统是一个基于Python开发的综合性交通基础设施评估工具，专门用于计算车辆荷载对桥梁结构产生的效应，并评估路线通行性。系统整合了路径规划、桥梁数据管理、效应计算和AI路径提取等多种功能，为交通管理和桥梁安全评估提供技术支持。

### 1.1 系统架构

系统采用模块化设计，主要包含以下核心组件：

- **API服务层**：基于FastAPI构建的RESTful API服务
- **计算引擎**：桥梁效应计算核心算法
- **数据管理**：桥梁和枢纽点数据查询与管理
- **路径规划**：枢纽点间路径查找与评估
- **地图服务**：高德地图API集成
- **AI服务**：基于GLM和Qwen模型的路径信息提取

## 2. 技术栈

- **后端框架**：FastAPI
- **数据处理**：NumPy, Pandas, SciPy
- **地图服务**：高德地图API
- **AI服务**：智谱GLM-4, 阿里云通义千问
- **异步处理**：asyncio, aiohttp
- **数据存储**：Excel文件系统

## 3. 核心模块详解

### 3.1 API服务模块 (bridge_api_v0.py)

系统的API入口，提供12个核心端点：

| 端点 | 功能描述 |
|------|----------|
| `/calculate_bridge_effect` | 计算单座桥梁的荷载效应 |
| `/find_bridges_on_road_section` | 查找路段上的桥梁 |
| `/evaluate_road_section_by_k_range` | 评估指定桩号范围的路段通行性 |
| `/find_path_between_junctions` | 查找枢纽点间路径 |
| `/evaluate_route_passability` | 评估路线通行性 |
| `/api_find_and_evaluate_routes` | 查找并评估多条路线 |
| `/api_find_and_evaluate_routes_with_amap` | 集成高德地图的路线评估 |
| `/refresh_cache` | 刷新数据缓存 |
| `/cache_status` | 获取缓存状态 |
| `/map_location_to_junction` | 位置映射到枢纽点 |
| `/map_locations_to_junctions` | 起终点映射到枢纽点 |
| `/extract_path_details` | 提取路径详情 |

### 3.2 桥梁效应计算模块 (bridge_effect_calculator.py)

系统的核心计算引擎，实现以下主要功能：

#### 3.2.1 单桥效应计算

```python
def calculate_bridge_effect(axle_weights, axle_distances, bridge_station)
```

- **输入参数**：
  - `axle_weights`: 轴重列表（吨）
  - `axle_distances`: 轴距列表（米）
  - `bridge_station`: 桥梁桩号

- **输出**：桥梁正弯矩、负弯矩、剪力的效应比值范围及通行条件

#### 3.2.2 路段评估

```python
def evaluate_road_section_by_k_range(highway_code, start_k, end_k, axle_weights, axle_distances)
```

评估指定桩号范围内所有桥梁的通行性，返回：
- 各桥梁的效应比值范围
- 路段整体通行性评估
- 最小效应比值

#### 3.2.3 长路线评估

```python
def evaluate_long_route_passability(route, axle_weights, axle_distances)
```

评估包含多段高速公路的长路线通行性，支持：
- 多高速公路组合路线
- 桥梁效应汇总计算
- 通行性综合判断

### 3.3 路径规划模块 (path_finder.py)

实现枢纽点间的路径查找功能：

#### 3.3.1 核心算法

- **深度优先搜索**：查找所有可能路径
- **最短路径算法**：基于距离的最优路径选择
- **路径去重**：避免重复路径

#### 3.3.2 主要功能

```python
def find_all_paths_between_junctions(start_junction, end_junction)
def find_shortest_path_between_junctions(start_junction, end_junction)
def calculate_route_similarity(route1, route2)
```

### 3.4 路径提取模块 (path_extractor.py)

基于AI模型的路径信息提取：

```python
async def extract_path_details_for_route(route_data)
async def extract_path_details_for_routes(routes_data)
```

从导航指令中提取关键路径节点，包括：
- 高速公路名称
- 枢纽、互通
- 收费站
- 桥梁和隧道
- 连接道路

### 3.5 路线评估模块 (route_evaluator.py)

整合路径查找和通行性评估：

```python
def find_and_evaluate_routes(start_junction, end_junction, axle_weights, axle_distances, max_routes=5)
```

功能流程：
1. 查找多条可行路径
2. 评估每条路径的通行性
3. 计算效应比值
4. 返回可通行路线列表

### 3.6 枢纽映射模块 (junction_mapper.py)

实现位置到枢纽点的映射：

#### 3.6.1 预定义枢纽点

从`facility_parameters/table/junctions.xlsx`读取预定义枢纽数据，包含：
- 枢纽点名称
- 经纬度坐标
- 区域信息

#### 3.6.2 动态映射

对于非预定义地点，通过高德地图API查找最近枢纽点：

```python
def map_location_to_junction(location_name)
def map_locations_to_junctions(start_location, end_location)
```

### 3.7 高德地图工具模块 (amap_utils.py)

集成高德地图API服务：

#### 3.7.1 核心功能

- **地理编码**：地址转经纬度
- **距离计算**：两点间驾车距离
- **路径规划**：获取详细导航路径
- **最近点查找**：查找最近的枢纽点

#### 3.7.2 异步处理

```python
async def async_get_route_with_amap(origin, destination)
async def async_add_amap_data_to_routes(routes)
```

支持批量路线处理，提高系统性能。

### 3.8 文件处理模块 (file_utils.py)

提供文件处理和缓存功能：

#### 3.8.1 数据读取

- 桥梁数据：`read_bridge_list_data()`
- 枢纽数据：`read_junctions_data()`
- 枢纽位置：`read_junctions_positions_data()`

#### 3.8.2 缓存机制

```python
def get_cached_bridge_data()
def get_cached_file_content(file_path)
```

减少文件I/O操作，提高系统响应速度。

### 3.9 桥梁数据查询模块 (bridge_data_query.py)

提供桥梁和枢纽点数据查询功能：

#### 3.9.1 桩号处理

```python
def extract_k_value(k_string)
def extract_bridge_k_value(bridge_id)
```

支持多种桩号格式的解析和转换。

#### 3.9.2 桥梁查找

```python
def find_bridges_on_road_section(junction1, highway_code, junction2)
def find_bridges_by_k_range(highway_code, start_k, end_k)
```

基于枢纽点或桩号范围查找桥梁。

### 3.10 AI聊天模块 (glm_chat.py & qwen_chat.py)

提供基于AI模型的路径信息提取功能：

#### 3.10.1 GLM-4集成

```python
def extract_path_string(path_data)
```

使用智谱GLM-4模型提取路径关键节点。

#### 3.10.2 通义千问集成

```python
def extract_path_string(path_data)
```

使用阿里云通义千问模型提取路径关键节点，支持思考模式切换。

## 4. 数据构成

### 4.1 桥梁数据

存储在`facility_parameters/table/bridge_list.xlsx`，包含以下字段：

| 字段名 | 描述 |
|--------|------|
| 桩号 | 桥梁位置标识 |
| 所属高速 | 所属高速公路代码 |
| 桥型 | 桥梁结构类型 |
| 跨径 | 桥梁跨径信息 |
| 公路等级 | 道路等级分类 |

### 4.2 枢纽点数据

存储在`facility_parameters/table/junctions.xlsx`，包含：

| 字段名 | 描述 |
|--------|------|
| junction_name | 枢纽点名称 |
| location | 经纬度坐标 |
| region | 所属区域 |

### 4.3 枢纽点位置数据

存储在`facility_parameters/table/junctions_positions.xlsx`，包含：

| 字段名 | 描述 |
|--------|------|
| junction_name | 枢纽点名称 |
| k_value | 桩号值 |
| highway_code | 高速公路代码 |

## 5. 系统工作流程

### 5.1 桥梁效应计算流程

1. **输入参数**：接收轴重、轴距和桥梁桩号
2. **数据查询**：从Excel文件读取桥梁数据
3. **效应计算**：应用结构力学公式计算荷载效应
4. **比值计算**：计算效应比值与设计值的比值
5. **结果返回**：输出正弯矩、负弯矩、剪力的效应比值范围

### 5.2 路线评估流程

1. **位置映射**：将起点终点映射到枢纽点
2. **路径查找**：查找所有可行路径
3. **桥梁筛选**：获取路径上的所有桥梁
4. **效应计算**：计算每座桥梁的荷载效应
5. **通行性评估**：判断路线整体通行性
6. **结果整合**：返回包含路径详情和评估结果的数据

### 5.3 AI路径提取流程

1. **数据准备**：组织起点、终点和导航指令
2. **模型调用**：向AI模型发送请求
3. **结果解析**：提取关键路径节点
4. **格式化输出**：生成标准路径字符串

## 6. 性能优化

### 6.1 缓存机制

- 桥梁数据缓存：减少Excel文件读取次数
- 文件内容缓存：缓存已读取的文件内容
- API响应缓存：缓存常用查询结果

### 6.2 异步处理

- 并发路径处理：使用asyncio处理多条路线
- 异步API调用：提高地图服务响应速度
- 批量数据处理：优化大数据量处理性能

### 6.3 计算优化

- NumPy向量化计算：提高数值计算效率
- SciPy插值算法：优化连续数据处理
- 并行计算：支持多核处理器并行计算

## 7. 部署与运行

### 7.1 环境要求

- Python 3.8+
- 依赖包：fastapi, uvicorn, numpy, pandas, scipy, openpyxl, requests, aiohttp, zai, openai

### 7.2 启动服务

```bash
cd d:/GitWorks/Traffic/Files/effect/calculator/bridge
python bridge_api_v0.py
```

### 7.3 API访问

服务启动后，可通过以下地址访问：
- API文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 8. 应用场景

### 8.1 交通管理

- 大件运输路线规划
- 超限车辆通行审批
- 桥梁安全评估

### 8.2 工程应用

- 桥梁荷载评估
- 路线可行性分析
- 交通影响评价

### 8.3 科研教学

- 桥梁工程研究
- 交通规划教学
- 算法验证平台

## 9. 技术特点

- 系统采用高度模块化的设计，各模块职责清晰，便于维护和扩展。
- 整合了桥梁数据、枢纽点数据、地图数据等多种数据源，提供全面的交通基础设施信息。
- 集成GLM-4和通义千问等先进AI模型，实现智能路径信息提取。
- 采用缓存机制、异步处理和并行计算等技术，确保系统高效运行。
- 基于FastAPI构建的RESTful API，提供完整的文档和交互式界面。

