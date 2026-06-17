# CargoNavigator 功能完整度 + 代码健康 改进设计

**日期**: 2026-06-17
**状态**: 已批准 → 待实现

---

## 1. 概述

### 1.1 目标

两轮迭代提升项目质量：
- **Round 1（P0 — 功能完整度）**：修复监控面板集成、验证 SSE 端到端流程、确保数字档案可用
- **Round 2（P1 — 代码健康）**：清理孤儿组件、统一 API 调用方式、搭建前端测试框架

### 1.2 当前状态审查

| 组件 | 行数 | 完成度 | 问题 |
|------|------|--------|------|
| `MonitorDashboard.vue` | 287行 | ~90% | 完整实现三栏大屏（地图2/3 + 检查点 + 告警）、SSE事件处理、marker移动。**未集成到 App.vue** |
| `DigitalArchive.vue` | 145行 | ~90% | 已集成，时间线+轨迹回放+检查点表格+JSON/PDF导出 |
| `TransportManager.vue` | 264行 | ~70% | 已集成，但监控UI仅半透明overlay，SSE代码与MonitorDashboard重复 |

---

## 2. Round 1：功能完整度

### 2.1 Architecture Decision

**将 MonitorDashboard 嵌入 TransportManager 作为监控模式**，而非作为独立页面或重写 TransportManager 的监控UI。

理由：
- MonitorDashboard 已完整实现设计文档要求的三栏大屏
- 避免在 TransportManager 中重复维护 SSE 消费逻辑
- 保留 MonitorDashboard 的独立模式能力（未来可独立使用）

### 2.2 TransportManager 改造

**文件**：`frontend/src/components/TransportManager.vue`

**变更**：

1. 新增 `monitoringMode` ref，控制右侧面板视图切换
2. 导入 MonitorDashboard，`v-if="monitoringMode"` 切换显示
3. **删除重复代码（~90行）**：
   - `connectSSE()` 函数
   - `updateVehicleMarker()` 函数
   - `currentGps`、`checkpoints`、`alerts` ref
   - `abortCtrl` 变量
   - `isMonitoring` ref（用 `monitoringMode` 替代）
   - `.monitor-overlay` 样式
4. `startMonitor()` 简化为：调用 API → 设置 `monitoringMode = true`
5. `stopMonitor()` 简化为：调用 API → 设置 `monitoringMode = false`

**模板切换逻辑**：

```
右侧面板:
  v-if="!selectedOrder"  →  空状态提示
  v-else-if="monitoringMode"  →  <MonitorDashboard embedded :order-id="selectedOrder.id" @done="monitoringMode = false" />
  v-else  →  订单详情卡片 + 小地图 + 操作按钮
```

左侧订单列表与状态筛选保持不变。

### 2.3 MonitorDashboard 适配

**文件**：`frontend/src/components/MonitorDashboard.vue`

**新增 Props**：

```javascript
const props = defineProps({
  orderId: { type: String, default: '' },     // 父组件传入的已选订单ID
  embedded: { type: Boolean, default: false }, // 嵌入模式 vs 独立模式
})
```

**新增 Emit**：

```javascript
const emit = defineEmits(['done', 'view-archive'])
```

**模板适配**：

- 订单选择器 (`q-select`)：`v-if="!embedded"` 隐藏
- 控制按钮行（开始/停止监控）：`v-if="!embedded"` 隐藏
- 嵌入模式下自动使用 `props.orderId`

**嵌入模式数据流**：

```
TransportManager                    MonitorDashboard (embedded)
─────────────────                   ──────────────────────────
1. startMonitoring(orderId) API     
   → 创建后端监控会话                
2. monitoringMode = true            
   → v-if 渲染组件                  3. onMounted: 自动 connectSSE(orderId)
                                    4. handleSSEEvent: GPS/checkpoint/alert
5. stopMonitoring(orderId) API      
   → 停止模拟 + 数据归档             
6. monitoringMode = false           
   → v-if 销毁组件                  7. onBeforeUnmount: abort SSE + destroy map
```

**关键**：嵌入模式下 MonitorDashboard 不调用 start/stop API，只负责 SSE 消费和 UI 渲染。API 调用由 TransportManager 管理。

**逻辑适配**：

- `onMounted()`: 若 `embedded && props.orderId`，自动调用 `connectSSE(props.orderId)`
- `stopMonitor()`: 在 `emit('done')` 通知父组件前先 `abortController.abort()` 断开 SSE
- 独立模式（`embedded=false`）行为不变：自己管理订单选择 + 调用 start/stop API

### 2.4 SSE 端到端验证清单

在 Docker 环境实际操作确认完整流程：

| # | 操作 | 预期结果 |
|---|------|---------|
| 1 | 路线规划 → 选路线 → 评估安全 → 生成许可证 → 创建运输单 | 订单状态 PERMIT_ISSUED |
| 2 | 运输管理 → 选中订单 → 开始运输 → 启动监控 | 右侧切换为 MonitorDashboard 大屏 |
| 3 | 等待 ~5秒 | 地图出现 marker 并沿路线移动，GPS 数据实时更新 |
| 4 | 等待通过检查点 | 检查点列表出现 ✅ 通过记录 |
| 5 | 等待随机异常注入 | 告警面板出现 🔴/🟡 告警条目 |
| 6 | 点击停止监控 | 监控模式退出，订单 COMPLETED |
| 7 | 切换到数字档案 → 点击订单 | GPS摘要 + 事件时间线 + 检查点明细 |
| 8 | 轨迹回放 tab | 地图显示完整路线 + 检查点标记 |
| 9 | JSON 导出 | 下载结构化 JSON |
| 10 | PDF 导出 | 下载 PDF 报告（或 text fallback） |

---

## 3. Round 2：代码健康

### 3.1 孤儿组件清理

删除以下 9 个不再被引用的组件：

| 组件 | 原因 |
|------|------|
| `MonitorDashboard.vue` | 已嵌入 TransportManager（Round 1 后变为由 TransportManager 导入，不再独立） |
| `TransportArchive.vue` | 已被 DigitalArchive.vue 替代 |
| `RouteForm.vue` | 已合并到 RoutePlanner.vue |
| `MapContainer.vue` | 已合并到 RoutePlanner.vue |
| `RouteResultPanel.vue` | 已合并到 RoutePlanner.vue |
| `SmartQA.vue` | 已被 AiAssistant.vue 替代 |
| `StatusDashboard.vue` | 已合并到 TransportManager.vue |
| `TransportTracker.vue` | 已合并到 TransportManager.vue |
| `VehicleProfileManager.vue` | 仅在 RouteForm.vue 中被注释掉引用 |

**注意**：Round 1 完成后 MonitorDashboard 被 TransportManager 导入使用，因此应从删除列表中移除。最终清理 8 个文件。

### 3.2 API 调用统一

**文件**：`frontend/src/components/TransportManager.vue`

`createTestOrder()` 当前直接 `axios.post`，改用已有 API 模块：

```javascript
// Before
const r = await axios.post(`${API_BASE}/api/v1/tracking/orders`, { ... })

// After
import { createOrder } from '@/api/tracking'
const r = await createOrder({ route_data, vehicle_info, assessment_data })
```

同时检查 `@/api/tracking.js` 是否已导出 `createOrder`，如没有则补充。

### 3.3 前端测试框架搭建

- 安装 vitest + @vue/test-utils + jsdom
- 创建 `frontend/vitest.config.js`
- 添加示例测试：`frontend/src/components/__tests__/AiAssistant.spec.js`
- 添加 `frontend/package.json` 的 `test` script

---

## 4. 文件清单

### Round 1 修改文件

| 文件 | 变更 | 影响行数 |
|------|------|---------|
| `frontend/src/components/TransportManager.vue` | 导入MonitorDashboard，删除重复SSE代码，新增monitoringMode | -90 / +15 |
| `frontend/src/components/MonitorDashboard.vue` | 新增props(embedded/orderId)，emit(done)，模板条件渲染 | +25 |

### Round 2 修改文件

| 文件 | 变更 |
|------|------|
| `frontend/src/components/` (8 files) | 删除 8 个孤儿组件 |
| `frontend/src/components/TransportManager.vue` | createTestOrder 改用 API 模块 |
| `frontend/src/api/tracking.js` | 补充 createOrder 导出（如缺失） |
| `frontend/vitest.config.js` | 新建 |
| `frontend/src/components/__tests__/AiAssistant.spec.js` | 新建示例测试 |
| `frontend/package.json` | 添加 test script + vitest 依赖 |

---

## 5. 自检

- [x] 无 TBD/TODO
- [x] MonitorDashboard 保留独立模式能力，不破坏现有功能
- [x] 删除列表已排除 MonitorDashboard（Round 1 后变为已使用）
- [x] 验证清单覆盖完整用户流程（规划→评估→监控→档案）
- [x] API 模块变更向后兼容
- [x] 不引入新的外部依赖（vitest 除外，且仅在 devDependencies）
