# 开发规范文档：大型货车智能选线系统

## 1. 概述
本文档旨在规范 **SmartRoute** 项目的开发流程、代码风格及测试标准，确保前后端功能完整且易于维护。随着项目的推进，本文档将持续更新。

## 2. 环境配置

### 2.1 目录结构
- **Backend**: `SmartRoute/backend`
- **Frontend**: `SmartRoute/frontend`
- **Tests**: `Test/` (用于存放独立测试脚本)
- **Docs**: `docs/SmartRoute/`

### 2.2 端口约定
| 服务 | 端口 | 说明 |
| :--- | :--- | :--- |
| **Frontend** | `6789` | Vue + Vite 开发服务器 (用户指定) |
| **Backend** | `9876` | FastAPI 开发服务器 |

## 3. 后端开发规范 (Backend)

### 3.1 技术栈
- **Framework**: FastAPI
- **Language**: Python 3.10+
- **Dependency Management**: `requirements.txt`

### 3.2 代码风格
- 遵循 PEP 8 规范。
- 使用 Type Hints (类型提示)。
- 接口定义在 `app/api/routes.py` 或模块化路由中。
- 业务逻辑封装在 `app/services/` 中。

### 3.3 测试规范
- **位置**: `d:\GitWorks\CargoNavigator\Test\`
- **工具**: `pytest`, `requests` / `httpx`
- **流程**:
    1. 确保后端服务运行 (`uvicorn app.main:app --reload`)。
    2. 运行 `Test/` 目录下的测试脚本对 API 进行黑盒测试。

## 4. 前端开发规范 (Frontend)

### 4.1 技术栈
- **Framework**: Vue 3 (Composition API)
- **UI Lib**: Quasar Framework
- **Build Tool**: Vite

### 4.2 配置要求
- 开发服务器端口必须设置为 **6789**。
- `vite.config.js` 中需显式配置 `server.port`。

### 4.3 目录规范
- `src/api/`: 存放 Axios 封装及 API 调用。
- `src/components/`: 通用组件。
- `src/pages/`: 页面组件。

## 5. 测试流程

### 5.1 完整性自测
1. **Backend Check**: 访问 `http://localhost:9876/health` 返回 `200 OK`。
2. **Frontend Check**: 访问 `http://localhost:6789` 能加载主页。
3. **Integration Check**: 前端能成功调用后端接口并展示数据。

### 5.2 自动化/脚本测试
- 在 `Test/` 目录下编写 Python 脚本，模拟前端请求，验证后端逻辑。

## 6. 版本控制
- 提交前请先运行测试。
- 保持 `.env` 文件不被提交 (包含 API Key)。
