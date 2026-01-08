# 架构设计文档：大型货车智能选线系统

## 1. 系统架构概览

```mermaid
graph TD
    User[用户] --> Frontend[前端 (Vue3 + Quasar)]
    Frontend -- HTTP/JSON --> Backend[后端 (FastAPI)]
    Backend -- HTTP --> AmapAPI[高德地图 Web API]
    Frontend -- JS SDK --> AmapJS[高德地图 JS API]
```

## 2. 模块详细设计

### 2.1 目录结构设计

```
d:\GitWorks\CargoNavigator\SmartRoute\
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py        # 路由定义
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # 配置加载 (Env)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py       # Pydantic 数据模型
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── amap_service.py  # 高德API封装
│   ├── requirements.txt
│   └── .env                     # 环境变量 (API Keys)
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/                 # Axios 封装
│   │   ├── components/          # Vue 组件
│   │   │   ├── MapContainer.vue # 地图组件
│   │   │   ├── RouteForm.vue    # 表单组件
│   │   ├── layouts/
│   │   ├── pages/
│   │   │   ├── IndexPage.vue    # 主页
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── quasar.config.js
│   └── package.json
└── README.md
```

### 2.2 接口契约 (API Contract)

#### 2.2.1 路径规划接口
- **Endpoint**: `POST /api/v1/routes/plan`
- **Description**: 根据起终点和车辆参数规划路线。
- **Request Body**:
```json
{
  "origin": "福建省三明厦钨新能源", // 或 "119.xxx,25.xxx"
  "destination": "福建省平潭跨境电商园",
  "vehicle": {
    "length": 13.5,    // 车长 (米)
    "width": 2.55,     // 车宽 (米)
    "height": 4.0,     // 车高 (米)
    "weight": 49.0,    // 车货总重 (吨)
    "axis_weight": 10.0 // 轴重 (吨)
  },
  "strategy": 0        // 选路策略 (0: 速度优先, 1: 费用优先等)
}
```
- **Response**:
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "routes": [
      {
        "id": "1",
        "distance": 150000, // 米
        "duration": 7200,   // 秒
        "path_points": "119.1,25.1;119.2,25.2...", // 用于前端绘图的路径点串
        "steps": [ ... ] // 详细导航段
      }
    ]
  }
}
```

#### 2.2.2 地点搜索接口 (可选，前端可直接调用JS API，也可后端代理)
- **Endpoint**: `GET /api/v1/places/search`
- **Query**: `keyword=厦门&city=350200`

### 2.3 数据流向
1. 用户在 `RouteForm` 组件输入起点、终点描述和车辆参数。
2. 前端调用后端 `plan_route` 接口。
3. 后端 `AmapService` 首先调用高德 `Geocoding API` 将地址转换为经纬度（如果前端传的是文本）。
4. 后端 `AmapService` 调用高德 `Direction API` (Truck/Driving) 获取路径数据。
5. 后端解析 API 响应，提取前端渲染所需的 `polyline` 坐标串和导航信息，返回给前端。
6. 前端 `MapContainer` 接收数据，使用 `AMap.Driving` 或 `AMap.Polyline` 在地图上绘制路线。

## 3. 技术约束
- **高德Key**: 后端需配置 Web服务 Key，前端需配置 Web端(JS API) Key。
- **跨域(CORS)**: FastAPI 需配置 CORS 中间件允许前端访问。

## 4. 依赖复用计划
- 复用 `d:\GitWorks\CargoNavigator\Files\effect\calculator\bridge\tools\amap_utils.py` 中的网络请求逻辑，但改写为异步 (async/await) 并移除原有的大量打印和与桥梁相关的逻辑。
- 复用 Pydantic 模型定义的思路。

## 5. 开发顺序
1. **Setup**: 初始化项目目录，配置 Python 和 Vue 环境。
2. **Backend**: 实现 FastAPI 基础框架和 AmapService。
3. **Frontend**: 初始化 Quasar 项目，实现地图加载。
4. **Integration**: 联调前后端接口，实现路线展示。
