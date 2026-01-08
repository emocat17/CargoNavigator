# 项目对齐文档：大型货车智能选线系统

## 1. 项目背景与目标

### 1.1 项目背景
当前大件运输/大型货车运输需要规划特定路线，现有系统 `CargoNavigator` 中包含了复杂的桥梁承载能力计算。用户希望剥离桥梁计算部分，专注于“智能选线”功能，并采用现代化的前后端分离架构进行重构。

### 1.2 核心目标
构建一个面向“大型货车”的智能选线系统，能够根据用户输入的起终点和车辆参数，利用高德地图API规划出合适的运输路线。

## 2. 需求分析与边界确认

### 2.1 原始需求
1. **输入**：起点、终点、车辆参数（如车长、车宽、车高、车重、轴重等）。
2. **处理**：调用高德地图API进行路径规划（需考虑货车策略）。
3. **输出**：可视化的路线展示及关键路线信息（距离、耗时、途经点等）。
4. **架构**：前后端分离。
    - 前端：Vue.js (Quasar Framework)
    - 后端：Python (FastAPI, 推荐)
5. **复用**：参考现有 `Files` 目录下的高德API集成代码，但**剔除**桥梁结构验算逻辑。

### 2.2 边界确认 (In/Out of Scope)
- **In Scope (包含)**:
    - 车辆参数录入界面。
    - 起终点地址解析（Geocoding）。
    - 高德地图路径规划接口调用（Driving API / Truck API）。
    - 路线在地图上的可视化展示。
    - 基础的路线信息展示（里程、时间）。
- **Out of Scope (不包含)**:
    - 桥梁结构承载能力验算（剪力、弯矩等）。
    - 复杂的审批流程（如Dify workflow中的审批逻辑，除非用于简单的路由）。
    - 爬虫系统（不需要爬取额外数据）。

## 3. 技术栈决策

### 3.1 前端
- **框架**: Vue 3
- **UI库**: Quasar Framework (支持Material Design，组件丰富，适合管理后台/工具类应用)
- **地图组件**: `@amap/amap-jsapi-loader` (推荐) 或直接引入高德JS API。

### 3.2 后端
- **语言**: Python 3.10+
- **框架**: FastAPI (高性能，易于构建REST API，现有代码中有相关配置参考)
- **依赖管理**: `requirements.txt` / `poetry` (建议使用 standard requirements.txt 保持简单)
- **地图服务**: 高德地图 Web服务 API

### 3.3 目录结构
```
SmartRoute/
├── backend/          # Python FastAPI 后端
│   ├── app/
│   │   ├── api/      # 路由定义
│   │   ├── core/     # 配置 (Env, Config)
│   │   ├── services/ # 业务逻辑 (AmapService)
│   │   └── schemas/  # Pydantic 模型
│   ├── main.py       # 入口
│   └── requirements.txt
├── frontend/         # Vue Quasar 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/ # API 请求封装
│   └── quasar.config.js
└── docs/             # 文档
```

## 4. 关键决策点与疑问 (Smart Decisions)

### 4.1 车辆参数具体包含哪些？
*决策*：参考高德地图货车路径规划API (Truck Direction) 的参数要求。
通常包括：
- `size`: 车辆大小 (1:微型货车, 2:轻型/蓝牌, 3:中型/黄牌, 4:重型)
- `height`: 车辆高度 (米)
- `width`: 车辆宽度 (米)
- `load`: 车辆总重 (吨)
- `weight`: 核定载重 (吨)
- `axis`: 轴数 (用于算费，选线可能影响限重)

### 4.2 高德API的选择
*决策*：
- 使用 **Web服务 API** (后端调用) 获取路线数据（路径点、距离、耗时）。
- 使用 **JS API** (前端) 进行地图渲染和轨迹绘制。
- 后端需要申请/配置 Key，前端也需要配置 JS API Key (及安全密钥)。
*注意*：现有代码中使用的是 Web API Key (`61ded56e661c7338f95ccafd0c4642d5`)，需确认是否支持货车路径规划（通常需要企业版或特定权限，普通版仅支持标准驾车）。
*假设*：先使用标准驾车API (`strategy`参数控制) 或 尝试货车API。如果Key受限，回退到标准驾车API但并在前端做参数标记。

### 4.3 现有代码复用
*决策*：
- 复用 `Files/effect/calculator/bridge/tools/amap_utils.py` 中的 `get_location` (地理编码) 和 `driving_direction` (路径规划) 逻辑，并进行封装和清理。

## 5. 结论
已明确需求，采用前后端分离架构，专注于货车/车辆维度的智能选线，剔除桥梁验算。下一步进行架构设计。
