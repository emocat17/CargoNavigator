# CargoNavigator -- 大件运输智能选线系统

基于高德地图 API 和 AI 评估的大件运输路线规划与监控平台。

> 对标江苏"秒批秒办"、广西AI平台、Bentley SUPERLOAD，为福建省大件运输提供一站式路线规划、桥梁安全评估、施工事件匹配、许可证生成、运输监控与数字档案管理。

## 核心功能

| 模块 | 功能 | 说明 |
|------|------|------|
| 路线规划 | 多策略并发选线 | 高德地图4策略并发（速度/费用/距离/避堵），自动去重排名 |
| 桥梁评估 | 荷载效应对比法 | 122座桥梁 + 153,900条影响线，7级通行评级（对标HVSAPS） |
| 施工匹配 | K值桩号精确匹配 | 66个施工事件与路线段落自动重叠检测 |
| 智能问答 | DeepSeek LLM + SSE | 法规知识库检索 -> 路线规划 -> 桥梁评估 -> 施工匹配 -> LLM合成 |
| 许可证生成 | 全自动填报 | 符合交通运输部令2021年第12号，I/II/III类自动分类 |
| 勘测清单 | 5类检查点 | 桥梁/隧道/收费站/匝道/高空障碍，优先级排序 |
| 运输追踪 | 10状态状态机 | DRAFT -> SUBMITTED -> ... -> IN_TRANSIT -> COMPLETED |
| 护送监控 | 实时地图大屏 | SSE推送GPS位置，Amap地图实时追踪，检查点+告警面板 |
| 数字档案 | 一键导出 | 完整轨迹回放 + 事件时间线 + JSON/PDF双格式导出 |

## 技术栈

| 层 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Quasar + Vite | Composition API，企业级组件 |
| 后端 | FastAPI + SQLAlchemy + Pydantic | 异步高并发，SSE流式推送 |
| 地图 | 高德 JS API v2.0 | 万级坐标流畅渲染 |
| LLM | DeepSeek API | 流式合成，法规知识检索 |
| 桥梁计算 | NumPy + SciPy | 影响线加载，效应比值计算 |
| 数据库 | SQLite (bridge.db + cargo_navigator.db) | 122桥/153900行，零配置 |
| 部署 | Docker Compose + Nginx | 一键启动，热重载开发 |

## 快速启动

### 前置条件

- Docker 28+ & Docker Compose v2.40+
- 高德地图 API Key（[免费申请](https://console.amap.com/dev/key/app)）
- DeepSeek API Key（[免费申请](https://platform.deepseek.com/api_keys)）

### 配置

```bash
# 编辑项目根目录 .env 文件，填入你的 API Key

# 必填
AMAP_API_KEY=你的高德地图key
DEEPSEEK_API_KEY=你的DeepSeek_api_key

# 可选 -- MaxKB 知识库
MAXKB_PORT=18090
MAXKB_USERNAME=admin
MAXKB_PASSWORD=admin123.
```

### 启动

```bash
# 开发模式（热重载 + 源码映射）
docker compose up -d --build

# 含 MaxKB 知识库
docker compose --profile kb up -d --build

# 生产模式
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 16789 | Vue SPA + Nginx |
| 后端 | 19876 | FastAPI REST API |
| MaxKB | 18090 | 知识库（需 `--profile kb`） |

### 访问

- **前端**: http://localhost:16789
- **API 文档**: http://localhost:19876/docs
- **健康检查**: http://localhost:19876/health
- **MaxKB 知识库**: http://localhost:18090（需 `--profile kb`）

### 热重载

Docker 开发模式下，修改代码即时生效：

| 修改位置 | 生效方式 |
|----------|---------|
| `frontend/src/*.vue` | Vite HMR 即时更新 |
| `backend/app/*.py` | uvicorn `--reload` 自动重启 |
| `package.json` / `requirements.txt` | 重新 `docker compose up -d --build` |

## 本地开发（不使用 Docker）

### 环境要求

- Python 3.12+
- Node.js 20+
- Git

### 启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 19876

# 前端（新终端）
cd frontend
npm install
npm run dev
```

前端 http://localhost:16789 | 后端 http://localhost:19876/docs

## 页面功能

| 页面 | 路径 | 功能 |
|------|------|------|
| 路线规划 | `/planner` | 起终点输入、多路线规划、安全评估、发证审批 |
| 运输管理 | `/transport` | 订单列表、状态管理、GPS 实时监控 |
| 数字档案 | `/archive` | 历史记录、轨迹回放、数据导出 |

## API 概览（42个端点）

| 前缀 | 端点数 | 功能 |
|------|--------|------|
| `/routes` | 3 | 路线规划、评估、比较 |
| `/vehicles` | 5 | 车辆档案CRUD + 分类 + 尺寸检查 |
| `/agent` | 5 | 智能问答(SSE) + 会话管理 |
| `/permit` | 3 | 许可证生成、预览、导出 |
| `/survey` | 1 | 勘测清单生成 |
| `/tracking` | 6 | 运输单CRUD + 状态机 + 统计 |
| `/monitor` | 4 | 监控启动/停止/SSE流/会话 |
| `/archive` | 2 | 档案查询 + JSON/PDF导出 |
| `/applications` | 5 | 申请CRUD |

## 许可证分类标准

| 类别 | 标准 | 审批时限 |
|------|------|---------|
| **I 类** | 高<=4.2m, 宽<=3m, 长<=20m | 5个工作日 |
| **II 类** | 高<=4.5m, 宽<=3.75m, 长<=28m, 重<=100t | 10个工作日 |
| **III 类** | 超出II类任一标准 | 20个工作日 |

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| AMAP_API_KEY | 高德地图 JS API Key | 是 |
| DEEPSEEK_API_KEY | AI 评估 LLM Key | 是 |
| DATABASE_URL | 主数据库连接 | 否（默认 SQLite） |
| MAXKB_PORT | MaxKB 知识库端口 | 否 |
| MAXKB_USERNAME | MaxKB 管理员用户名 | 否 |
| MAXKB_PASSWORD | MaxKB 管理员密码 | 否 |

## 项目结构

```
CargoNavigator/
├── docker-compose.yml          # 开发环境（默认）
├── docker-compose.prod.yml     # 生产环境覆盖
├── .env                        # 环境变量配置（API Key等）
│
├── backend/
│   ├── Dockerfile              # 生产镜像（多阶段构建）
│   ├── Dockerfile.dev          # 开发镜像（热重载）
│   ├── requirements.txt
│   ├── bootstrap.py            # 启动前检查
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── api/                # API 路由（8个模块）
│   │   │   ├── routes.py           # 路线规划
│   │   │   ├── assessment_routes.py # 路线评估
│   │   │   ├── agent_routes.py     # 智能问答(SSE)
│   │   │   ├── permit_routes.py    # 许可证生成
│   │   │   ├── survey_routes.py    # 勘测清单
│   │   │   ├── tracking_routes.py  # 运输追踪
│   │   │   ├── monitor_routes.py   # 护送监控+档案
│   │   │   └── vehicle_routes.py   # 车辆管理
│   │   ├── services/           # 业务逻辑（15个服务）
│   │   ├── models/             # 数据模型
│   │   └── schemas/            # Pydantic 模型
│   ├── data/
│   │   ├── cargo_bridge.db     # 桥梁数据库（122桥/153900行）
│   │   ├── schema.sql          # 表结构
│   │   └── migrate_data.py     # 数据迁移脚本（手动）
│   └── tests/                  # 362个测试
│
├── frontend/
│   ├── Dockerfile              # 生产镜像（nginx）
│   ├── Dockerfile.dev          # 开发镜像（Vite）
│   ├── vite.config.js
│   └── src/
│       ├── App.vue             # 主布局
│       ├── api/                # API模块（8个）
│       └── components/         # 组件
│           ├── RouteForm.vue       # 路线规划表单
│           ├── SmartQA.vue         # 智能问答(SSE)
│           ├── StatusDashboard.vue # 运输追踪面板
│           ├── MonitorDashboard.vue # 护送监控大屏
│           ├── TransportArchive.vue # 数字档案查看器
│           └── ...
│
└── docs/
    ├── deployment.md
    ├── superpowers/specs/      # 设计文档
    └── reference/              # 参考资料
```

## 开发

```bash
# 后端测试
docker compose exec backend pytest -x -q

# 前端测试
cd frontend && npx vitest run

# 类型检查
docker compose exec backend mypy app/ --ignore-missing-imports
```

## License

Proprietary -- All rights reserved.

---

> **CargoNavigator** -- 让每一吨大件运输都安全、合规、高效。
