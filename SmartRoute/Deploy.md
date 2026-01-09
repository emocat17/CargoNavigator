# SmartRoute (大型货车智能选线系统) 部署文档

本文档详细说明了 SmartRoute 系统的源码部署、启动步骤以及自定义配置方法。

## 1. 环境准备

在开始部署之前，请确保您的开发环境满足以下要求：

- **操作系统**: Windows / macOS / Linux
- **Python**: 3.10 或更高版本 (用于后端)
- **Node.js**: 16.0 或更高版本 (用于前端)
- **Git**: 用于代码版本控制

## 2. 后端部署 (Backend)

后端基于 FastAPI 框架开发，使用 SQLite 数据库。

### 2.1 进入后端目录
```bash
cd SmartRoute/backend
```

### 2.2 创建虚拟环境 (推荐)
为了避免依赖冲突，建议创建 Python 虚拟环境。

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3 安装依赖
```bash
pip install -r requirements.txt
```

### 2.4 配置环境变量
在 `SmartRoute/backend` 目录下创建一个 `.env` 文件（可复制 `.env.example`），并配置高德地图 API Key：

```ini
# .env 文件内容
AMAP_API_KEY=your_backend_web_service_api_key
DATABASE_URL=sqlite:///./data/cargo_navigator.db
```
> **注意**: 后端使用的是高德地图 **Web 服务** Key，与前端使用的 JS API Key 不同。

### 2.5 启动后端服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 9876
```
启动成功后，访问 `http://localhost:9876/docs` 可查看 API 文档。
数据库文件将自动生成在 `backend/data/` 目录下。

---

## 3. 前端部署 (Frontend)

前端基于 Vue 3 + Vite + Quasar 框架开发。

### 3.1 进入前端目录
```bash
cd SmartRoute/frontend
```

### 3.2 安装依赖
```bash
npm install
```

### 3.3 配置环境变量
在 `SmartRoute/frontend` 目录下创建一个 `.env` 文件（可复制 `.env.example`）：

```ini
# 高德地图 JS API Key (Web端(JSAPI))
VITE_AMAP_KEY=your_frontend_js_api_key

# 高德地图安全密钥 (与 JS API Key 绑定)
VITE_AMAP_SECURITY_CODE=your_security_code

# 是否启用数据导出功能 (true/false)
VITE_ENABLE_DATA_EXPORT=true
```

### 3.4 启动开发服务器
```bash
npm run dev
```
启动成功后，控制台会显示访问地址，默认为：
`http://localhost:6789`

---

## 4. 自定义配置教程

### 4.1 自定义后端端口
默认后端运行在 `9876` 端口。

**修改启动命令:**
在启动时通过 `--port` 参数指定新端口（例如 8000）：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
> **注意**: 修改后端端口后，需要同步修改前端 `src/api/*.js` 中的请求 Base URL。

### 4.2 自定义前端端口
默认前端运行在 `6789` 端口。

**修改配置文件:**
打开 `SmartRoute/frontend/vite.config.js` 文件，找到 `server` 配置项：

```javascript
export default defineConfig({
  server: {
    port: 6789, // 修改此处的数字为您想要的端口
    host: '0.0.0.0'
  },
  // ... 其他配置
})
```
修改保存后，重新运行 `npm run dev` 即可生效。

### 4.3 跨域配置 (CORS)
如果修改了前端或后端的端口，导致跨域问题，请检查后端 `app/main.py` 中的 CORS 配置：

```python
# SmartRoute/backend/app/main.py

origins = [
    "http://localhost",
    "http://localhost:6789", # 前端端口
    "http://localhost:9876", # 后端端口
    "*"                      # 允许所有来源 (生产环境请修改)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # ...
)
```

## 5. 生产环境构建

### 前端构建
```bash
cd SmartRoute/frontend
npm run build
```
构建产物位于 `frontend/dist` 目录，可使用 Nginx 等 Web 服务器进行托管。

### 后端部署
建议使用 Gunicorn (Linux/macOS) 或 Uvicorn (Windows) 配合 Supervisor 或 Systemd 进行进程管理。
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```
