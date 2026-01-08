# SmartRoute - 大型货车智能选线系统

## 项目简介
本项目旨在为大型货车提供智能化的路线规划服务。通过输入起终点和车辆参数（长、宽、高、重），结合高德地图API，计算并展示最优运输路线。

## 目录结构
- `backend/`: Python FastAPI 后端服务
- `frontend/`: Vue 3 + Quasar 前端应用
- `docs/`: 项目文档 (位于项目根目录的 docs/SmartRoute)

## 快速开始

### 后端
1. 进入 `backend` 目录
2. 安装依赖: `pip install -r requirements.txt`
3. 启动服务: `uvicorn app.main:app --reload`

### 前端
1. 进入 `frontend` 目录
2. 安装依赖: `npm install`
3. 启动开发服务器: `npm run dev`

## 技术栈
- **后端**: FastAPI, Python 3.10+, httpx
- **前端**: Vue 3, Quasar Framework, Amap JS API
