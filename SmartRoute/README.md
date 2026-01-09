# SmartRoute - 大型货车智能选线系统

> 🚛 **专为大型货车设计的智能路线规划与通行资质管理平台**

SmartRoute 是一个前后端分离的现代化 Web 应用，旨在解决大型货车在运输过程中的路线规划难题。它不仅提供基于高德地图的多策略路线规划（速度优先、费用优先、距离优先等），还集成了车辆通行资质预审功能，帮助运输企业降本增效，规避限行风险。

## 🌟 核心功能

### 1. 智能路线规划
- **多策略支持**: 支持“速度优先”、“费用优先”、“距离优先”、“躲避拥堵”四种策略。
- **多路线对比**: 一次查询返回 N 条（默认 3 条）备选路线，供用户根据实际情况选择。
- **精准成本估算**: 
  - **路费**: 基于高德 API 的实时过路费数据。
  - **油费**: 根据里程、红绿灯数量及重卡平均油耗（35L/100km）进行精准估算。
  - **总费用**: 直观展示“路费 + 油费”的总成本。
- **安全提醒**: 自动检测并提示“长途驾驶疲劳提醒”及“夜间行车安全提醒”（2:00-5:00）。
- **隧道统计**: 自动统计路线中的隧道数量及总长度，辅助安全决策。

### 2. 通行资质预审管理
- **独立模块**: 提供独立的通行资质信息录入与管理界面。
- **全流程覆盖**: 涵盖“申请人信息”、“车辆配置”、“货物信息”、“运输计划”四大维度。
- **数据持久化**: 支持本地存储（LocalStorage）与后端数据库（SQLite）双重备份，防止数据丢失。
- **车辆画像**: 支持配置详细的车辆参数（长宽高、轴重、轴距等），为后续的合规性检查提供数据基础。

### 3. 高性能交互体验
- **流畅地图渲染**: 采用动态路段合并算法，大幅降低长途路线的渲染开销，切换路线丝般顺滑。
- **数据压缩传输**: 后端启用 Gzip 压缩，大幅减少网络传输体积，弱网环境下加载更快。
- **数据导出**: 支持将规划结果及车辆配置一键导出为 JSON 文件（可通过配置开启）。

---

## 🛠 技术架构

### 后端 (Backend)
- **框架**: [FastAPI](https://fastapi.tiangolo.com/) (高性能 Python Web 框架)
- **数据库**: SQLite + [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- **地图服务**: 高德地图 Web 服务 API (用于路径规划、地理编码)
- **依赖管理**: `requirements.txt`

### 前端 (Frontend)
- **框架**: [Vue 3](https://vuejs.org/) (Composition API)
- **UI 组件库**: [Quasar Framework](https://quasar.dev/) (Material Design 风格)
- **构建工具**: [Vite](https://vitejs.dev/) (极速开发体验)
- **地图引擎**: 高德地图 JS API 2.0 (AMap)

---

## 📂 目录结构说明

```
SmartRoute/
├── backend/                # 后端项目根目录
│   ├── app/                # 应用源码
│   │   ├── api/            # API 路由定义 (routes.py, application_routes.py)
│   │   ├── models/         # 数据模型 (SQLAlchemy ORM & Pydantic Schemas)
│   │   ├── services/       # 业务逻辑层 (AmapService, ApplicationService)
│   │   ├── core/           # 核心配置
│   │   └── main.py         # 程序入口
│   ├── data/               # SQLite 数据库文件存放目录
│   ├── .env.example        # 后端环境变量示例
│   └── requirements.txt    # Python 依赖列表
│
├── frontend/               # 前端项目根目录
│   ├── src/                # 源码目录
│   │   ├── api/            # API 接口封装
│   │   ├── components/     # Vue 组件 (RouteForm, MapContainer, QualificationManager 等)
│   │   └── pages/          # 页面组件
│   ├── .env.example        # 前端环境变量示例
│   ├── vite.config.js      # Vite 配置文件
│   └── package.json        # Node.js 依赖列表
│
├── Deploy.md               # 详细部署与配置文档
└── README.md               # 项目概览文档 (本文档)
```

---

## 🚀 快速开始

详细的部署步骤请参考 [Deploy.md](./Deploy.md)。

### 简要步骤

1.  **环境准备**: 确保安装 Python 3.10+ 和 Node.js 16+。
2.  **后端启动**:
    ```bash
    cd backend
    pip install -r requirements.txt
    # 复制 .env.example 为 .env 并填入高德 Key ： AMAP_API_KEY=5bfa19c817023152291ef88057477fcd
    uvicorn app.main:app --reload --host 0.0.0.0 --port 9876
    ```
3.  **前端启动**:
    ```bash
    cd frontend
    npm install
    # 复制 .env.example 为 .env 并填入高德 Key
    VITE_AMAP_KEY=0625539f7941518573845dd16fe22316
    VITE_AMAP_SECURITY_CODE=cef9db5af022e4b888d8ec2029b4651b
    npm run dev
    ```
4.  **访问应用**: 打开浏览器访问 `http://localhost:6789`。

---

## 📝 贡献指南

欢迎提交 Issue 或 Pull Request 来改进本项目。
开发时请遵循现有的代码规范：
- 后端遵循 PEP 8。
- 前端遵循 Vue 3 Composition API 最佳实践。

## 📄 许可证

[MIT License](LICENSE)
