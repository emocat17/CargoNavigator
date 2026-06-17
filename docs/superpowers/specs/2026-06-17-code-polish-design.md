# CargoNavigator 精细化打磨 — 设计文档

> **目标**: 3轮20项修复，从安全加固到结构优化，将项目打磨到生产级质量。

## Round 1: 安全+质量修复（10项）

### R1.1 API 密钥泄露修复

**问题**: `frontend/.env.production` 含有真实高德密钥 `0625539f...` 和安全码 `cef9db5a...`，已提交 git 历史。4个 Vue 组件中硬编码相同密钥作为 JS fallback。

**修复**:
- `git rm --cached frontend/.env.production` 停止追踪
- 根 `.gitignore` 添加 `*.env.production` 规则
- TransportManager.vue、RoutePlanner.vue、MonitorDashboard.vue、DigitalArchive.vue 中移除硬编码 fallback，改为仅使用 `import.meta.env.VITE_AMAP_KEY`，无配置时 console.error 给出明确提示

### R1.2 裸 `except: pass`

**位置**: `backend/app/api/routes.py:515`

**修复**: `except:` → `except (ValueError, TypeError):`，添加 `logger.warning()`

### R1.3 `print()` → `logging`

**位置**: bridge_db.py(1), main.py(2), routes.py(4)

**修复**: 全部替换为对应级别的 `logger.info/warning/error`，补充上下文信息

### R1.4 前端 console 清理

- 2处 `console.log` 删除
- 5处 `console.error` 补充 `$q.notify()` 用户可见反馈

### R1.5 后端 exception 规范化

- `traffic_service.py:81` → `except (ValueError, TypeError): logger.debug()`
- `agent_routes.py:159` → `except Exception as e: logger.error()`
- 7处 `except Exception:` 无变量 → 补充 `as e`

### R1.6 垃圾文件清理

- `git rm --cached page-docker.txt`

---

## Round 2: 高质量提升（6项）

### R2.1 前端测试补齐

为核心组件补充 vitest 测试：
- **TransportManager**: 订单列表渲染、状态筛选、createTestOrder 调用、startMonitor 触发
- **MonitorDashboard**: 嵌入式 props、SSE 事件解析、done emit
- **RoutePlanner**: 路线规划触发、方案选择、按钮状态

每组件 3-5 个测试用例。

### R2.2 VehicleWizard 拆分

988行 → 拆分为：
- `VehicleWizard.vue` (~200行) — 步骤导航+状态管理
- `VehicleFormStep.vue` (~300行) — 车辆参数表单
- `AxleConfigStep.vue` (~250行) — 轴重配置
- `ReviewConfirmStep.vue` (~200行) — 审核确认

### R2.3 API fallback 规范化

- `api/index.js` 统一导出 BASE，未配置时 warn
- 9个 API 模块从 index.js 导入，移除各模块的硬编码 fallback

### R2.4 nginx 配置独立文件

- 创建 `frontend/nginx.conf`，替代 Dockerfile 中的 inline echo
- Dockerfile 改为 `COPY nginx.conf`

### R2.5 .gitignore 补充

新增: `*.db-journal`, `*.env.production`, `page-*.txt`

### R2.6 占位数据清理

`permit_routes.py` 中 `91350000XXXXXXXXXX` → 从配置读取或返回错误

---

## Round 3: 结构优化（4项）

### R3.1 引入 vue-router

- 安装 `vue-router@4`
- 3条路由: `/planner`、`/transport`、`/archive`
- `App.vue` 用 `<router-view>` 替代 `v-show`
- 底部导航用 `router.push()`
- 共享状态保留在 `store/index.js`

### R3.2 Dockerfile 镜像源解耦

- 4个 Dockerfile 中将硬编码镜像 URL 改为 ARG 参数（默认保留中国镜像）
- `docker-compose.yml` 通过 `args` 传入

### R3.3 Python 类型标注

核心3服务补充类型标注：
- `monitor_service.py` — 补全返回值
- `route_assessor.py` — 参数+返回值
- `tracking_service.py` — 状态机关键路径

### R3.4 README 更新

补充: 快速启动、端口说明、环境变量、技术栈，约60行。

---

## 执行策略

3轮顺序执行，每轮完成后：
1. 运行全部测试（backend pytest + frontend vitest）
2. `docker compose up -d --build` 验证无报错
3. 独立 git commit
4. 确认通过后进入下一轮

## 验证标准

- [ ] `git status` 干净，无污染文件
- [ ] `docker compose up -d --build` 成功，3服务健康
- [ ] 前端 console 0 errors 0 warnings
- [ ] 后端 `docker compose logs backend | grep -i error` 无异常
- [ ] 前端所有测试通过
- [ ] 后端所有测试通过
- [ ] E2E 流程: 规划→评估→运输→监控→归档 全链路正常
