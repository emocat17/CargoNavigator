# 功能完整度 + 代码健康 改进实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已完整实现的 MonitorDashboard 嵌入 TransportManager 作为监控模式，清理 8 个孤儿组件，统一 API 调用方式，搭建前端测试框架。

**Architecture:** TransportManager 新增 monitoringMode 状态，v-if 切换 MonitorDashboard（embedded 模式）。MonitorDashboard 新增 embedded/orderId props，嵌入模式下隐藏控制栏、自动连接 SSE，由父组件管理 API 调用。随后清理孤儿文件、统一 API 导入、安装 vitest。

**Tech Stack:** Vue 3, Quasar, Vite, vitest, @vue/test-utils, jsdom

---

## Round 1：功能完整度

### Task 1: TransportManager 改造 — 集成 MonitorDashboard 监控模式

**Files:**
- Modify: `frontend/src/components/TransportManager.vue`

**Current behavior:** 监控时显示半透明 overlay（~20行 CSS），SSE 消费代码（~80行）与 MonitorDashboard 重复。
**Target behavior:** 监控时右侧面板切换为 `<MonitorDashboard embedded :order-id="..." @done="..." />`，删除重复代码。

- [ ] **Step 1: 在 script 顶部新增 import 和 monitoringMode ref**

在 `TransportManager.vue` 的 `<script setup>` 中：

1. 新增 import（在现有 import 后追加）：
```javascript
import MonitorDashboard from './MonitorDashboard.vue'
```

2. 在现有 `import { getOrders, updateOrderStatus } from '@/api/tracking'` 行，改为同时导入 `createOrder`：
```javascript
import { createOrder, getOrders, updateOrderStatus } from '@/api/tracking'
```

3. 删除不再需要的 import：
```javascript
// 删除这行（MonitorDashboard 内部已导入）
import { startMonitoring, getStreamUrl, stopMonitoring } from '@/api/monitor'
```

4. 新增 `monitoringMode` ref（在 `const actionLoading = ref(false)` 之后）：
```javascript
const monitoringMode = ref(false)
```

5. **删除** 以下不再需要的变量/ref（共 ~6 行）：
```javascript
const isMonitoring = ref(false)    // ← 用 monitoringMode 替代
const currentGps = ref(null)       // ← MonitorDashboard 内部管理
const checkpoints = ref([])        // ← MonitorDashboard 内部管理
const alerts = ref([])             // ← MonitorDashboard 内部管理
```
以及变量声明区：
```javascript
let abortCtrl = null               // ← MonitorDashboard 内部管理
```

- [ ] **Step 2: 删除重复的 SSE 消费函数**

删除以下函数（整个函数体）：
- `connectSSE()` — 第 216-237 行
- `updateVehicleMarker()` — 第 239-245 行

- [ ] **Step 3: 简化 startMonitor() 和 stopMonitor()**

将现有的 `startMonitor()` 函数（第 205-213 行）替换为：

```javascript
async function startMonitor() {
  if (!selectedOrder.value) return
  try {
    const r = await startMonitoring(selectedOrder.value.id)
    if (r.code === 200) {
      monitoringMode.value = true
      $q.notify({ type: 'positive', message: '监控已启动' })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || '启动失败' })
  }
}
```

将现有的 `stopMonitor()` 函数（第 247-250 行）替换为：

```javascript
async function stopMonitor() {
  if (!selectedOrder.value) return
  try {
    const r = await stopMonitoring(selectedOrder.value.id)
    monitoringMode.value = false
    selectedOrder.value.status = 'COMPLETED'
    $q.notify({ type: 'positive', message: `归档: ${r.data?.gps_points_saved || 0} GPS点` })
  } catch (e) {
    $q.notify({ type: 'negative', message: '停止失败' })
  }
}
```

注意：`startMonitor()` 和 `stopMonitor()` 仍需要 `startMonitoring` 和 `stopMonitoring`，保留这两个 import：
```javascript
import { startMonitoring, stopMonitoring } from '@/api/monitor'
```

- [ ] **Step 4: 更新模板 — 右侧面板切换逻辑**

将模板中右侧面板的 `<template v-else>` 块替换为：

```html
      <template v-else>
        <!-- 监控模式：全屏 MonitorDashboard -->
        <div v-if="monitoringMode" class="col column" style="flex:1;">
          <MonitorDashboard
            embedded
            :order-id="selectedOrder.id"
            @done="monitoringMode = false"
          />
        </div>

        <!-- 正常模式：详情卡片 + 小地图 -->
        <template v-else>
          <!-- 详情卡片 -->
          <div class="q-pa-sm bg-white" style="border-bottom:1px solid #e2e8f0;">
            <div class="row items-center">
              <span class="text-h6">{{ selectedOrder.order_number }}</span>
              <q-badge :color="statusColor(selectedOrder.status)" :label="selectedOrder.status" class="q-ml-sm" />
              <q-space />
              <!-- 操作按钮 -->
              <template v-if="selectedOrder.status === 'PERMIT_ISSUED'">
                <q-btn color="positive" icon="play_arrow" label="开始运输" dense size="sm" @click="startTransport" :loading="actionLoading" />
              </template>
              <template v-if="selectedOrder.status === 'IN_TRANSIT' && !monitoringMode">
                <q-btn color="primary" icon="monitor_heart" label="启动监控" dense size="sm" @click="startMonitor" />
              </template>
              <template v-if="monitoringMode">
                <q-btn color="red" icon="stop" label="停止监控" dense size="sm" @click="stopMonitor" />
              </template>
              <template v-if="selectedOrder.status === 'COMPLETED'">
                <q-btn color="secondary" icon="archive" label="查看档案" dense size="sm" @click="$emit('view-archive', selectedOrder.id)" />
              </template>
            </div>
            <!-- 状态时间线 -->
            <div class="row q-gutter-xs q-mt-xs text-caption">
              <span v-for="(s, i) in statusTimeline" :key="i" :class="s.done ? 'text-green' : 'text-grey-4'">
                {{ s.label }} {{ i < statusTimeline.length - 1 ? '→' : '' }}
              </span>
            </div>
          </div>

          <!-- 地图/监控区域 -->
          <div class="col" style="flex:1; position:relative;">
            <div id="transport-map" style="width:100%;height:100%;"></div>
          </div>
        </template>
      </template>
```

关键变更：
- 最外层用 `v-if="monitoringMode"` 渲染 MonitorDashboard，`v-else` 渲染原有详情+地图
- 删除了 `.monitor-overlay` 卡片（原第 78-86 行的 overlay div）
- "启动监控"按钮条件从 `isMonitoring` 改为 `!monitoringMode`
- "停止监控"按钮移到监控模式判断之外，显示条件从 `isMonitoring` 改为 `monitoringMode`

- [ ] **Step 5: 清理样式**

删除 `.monitor-overlay` 样式块（原第 263 行）：
```css
/* 删除这行 */
.monitor-overlay { position: absolute; top: 8px; left: 8px; right: 8px; z-index: 100; }
```

- [ ] **Step 6: 更新 onBeforeUnmount**

将现有的 `onBeforeUnmount` 改为只清理 transportMap（abortCtrl 已删除）：
```javascript
onBeforeUnmount(() => { if (transportMap) transportMap.destroy() })
```

- [ ] **Step 7: 验证构建**

在 `frontend/` 目录运行：
```bash
npm run build
```
预期：构建成功，无 import 错误，无未使用变量警告。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/TransportManager.vue
git commit -m "refactor(TransportManager): 集成MonitorDashboard替代内联监控，删除重复SSE代码"
```

---

### Task 2: MonitorDashboard 适配 — embedded 模式

**Files:**
- Modify: `frontend/src/components/MonitorDashboard.vue`

- [ ] **Step 1: 新增 props 定义**

在 `<script setup>` 顶部（`const $q = useQuasar()` 之后）新增：

```javascript
const props = defineProps({
  orderId: { type: String, default: '' },
  embedded: { type: Boolean, default: false },
})
```

- [ ] **Step 2: 更新 emit 定义**

将现有的 `const emit = defineEmits(['view-archive'])` 改为：

```javascript
const emit = defineEmits(['view-archive', 'done'])
```

- [ ] **Step 3: 模板中隐藏控制栏（嵌入模式）**

在模板的控制栏 div（`<div class="row q-mb-sm q-col-gutter-sm items-center">`）上添加 `v-if`：

```html
<div v-if="!embedded" class="row q-mb-sm q-col-gutter-sm items-center">
```

- [ ] **Step 4: 添加停止按钮（嵌入模式）**

在嵌入模式下，Info Bar 右侧增加一个停止监控按钮。在 Info Bar 的 `<div v-if="currentGps" ...>` 块内部末尾（`</div>` 前）添加：

```html
              <q-space />
              <q-btn v-if="embedded" color="red" icon="stop" label="停止监控" dense size="sm" @click="stopMonitor" />
```

完整替换 Info Bar：
```html
	    <div v-if="currentGps" class="row q-mb-sm q-col-gutter-sm text-caption bg-blue-1 q-pa-xs rounded-borders items-center">
	      <div class="col-auto">&#x1F4CD; {{ currentGps.lon }}, {{ currentGps.lat }}</div>
	      <div class="col-auto">&#x1F3C3; {{ currentGps.speed }} km/h</div>
	      <div class="col-auto">&#x1F9ED; {{ currentGps.heading }}&deg;</div>
	      <div class="col-auto">&#x1F3AF; 剩余 {{ currentGps.distance_remaining }} km</div>
	      <q-space />
	      <div class="col-auto">
	        <q-btn v-if="embedded" color="red" icon="stop" label="停止监控" dense size="sm" @click="stopMonitor" />
	      </div>
	    </div>
```

- [ ] **Step 5: onMounted 支持嵌入模式自动连接**

将现有 `onMounted` 替换为：

```javascript
onMounted(async () => {
  if (props.embedded) {
    // 嵌入模式：父组件已调用 start API，直接连接 SSE
    if (props.orderId) {
      isMonitoring.value = true
      await nextTick()
      initMap()
      connectSSE(props.orderId)
    }
  } else {
    // 独立模式：加载订单列表 + 初始化地图
    await loadOrders()
    await nextTick()
    initMap()
  }
})
```

- [ ] **Step 6: startMonitor 适配嵌入模式**

在 `startMonitor()` 函数开头添加嵌入模式保护（嵌入模式下不应直接调用此函数，但做防御）：

```javascript
async function startMonitor() {
  if (props.embedded) {
    // 嵌入模式下由父组件管理 API 调用，这里直接连接 SSE
    if (!props.orderId) return
    isMonitoring.value = true
    alerts.value = []
    checkpoints.value = []
    connectSSE(props.orderId)
    return
  }
  // ... 原有独立模式代码保持不变 ...
```

- [ ] **Step 7: stopMonitor 适配嵌入模式**

修改 `stopMonitor()` 函数，在末尾 emit('done')：

找到 `stopMonitor()` 函数中的成功分支（`if (res.code === 200)` 块），在 `$q.notify(...)` 之后添加：

```javascript
      if (props.embedded) {
        emit('done')
      }
```

完整替换 `stopMonitor()` 函数：

```javascript
async function stopMonitor() {
  if (props.embedded) {
    // 嵌入模式：断开 SSE，通知父组件
    if (abortController) { abortController.abort(); abortController = null }
    isMonitoring.value = false
    emit('done')
    return
  }
  // 独立模式：调用 API 停止 + 归档
  if (!selectedOrderId.value) return
  try {
    if (abortController) { abortController.abort(); abortController = null }
    const res = await stopMonitoring(selectedOrderId.value)
    if (res.code === 200) {
      isMonitoring.value = false
      $q.notify({
        type: 'positive',
        message: `已归档: ${res.data.gps_points_saved}GPS点, ${res.data.checkpoints_saved}检查点`
      })
      emit('view-archive', selectedOrderId.value)
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || '停止失败' })
  }
}
```

- [ ] **Step 8: 验证构建**

```bash
cd frontend && npm run build
```
预期：构建成功。

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/MonitorDashboard.vue
git commit -m "feat(MonitorDashboard): 新增embedded模式支持，嵌入TransportManager时自动连接SSE"
```

---

### Task 3: SSE 端到端验证

**Files:** 无代码修改，手动验证。

- [ ] **Step 1: 启动 Docker 环境**

```bash
docker compose up -d --build
```
预期：3个服务 (cargo-backend, cargo-frontend, cargo-maxkb) 全部 running。

- [ ] **Step 2: 完整流程验证**

打开 `http://localhost:16789`，按以下顺序操作：

| # | 操作 | 预期结果 |
|---|------|---------|
| 1 | 路线规划 → 输入起终点 → 开始规划 → 选方案2 | 地图显示3条路线 |
| 2 | 点击"评估安全" | 显示评估报告面板 |
| 3 | 点击"生成许可证" | 许可证生成成功通知 |
| 4 | 切换到运输管理 → "新建运输单" | 创建成功，状态 PERMIT_ISSUED |
| 5 | 选中订单 → "开始运输" → "启动监控" | 右侧切换为 MonitorDashboard 大屏 |
| 6 | 等待 5-10 秒 | 地图出现 marker 并沿路线移动，GPS数据实时更新 |
| 7 | 等待检查点通过 | 检查点列表出现 ✅ 记录 |
| 8 | 等待告警（4%概率/5秒） | 告警面板出现条目 |
| 9 | 在 MonitorDashboard 中点击"停止监控" | 监控退出，订单 COMPLETED |
| 10 | 切换到数字档案 → 点击订单 | GPS摘要 + 事件时间线 + 检查点明细 |
| 11 | 切换到"轨迹回放"tab | 地图显示路线 + 检查点标记 |
| 12 | 点击"JSON"导出 | 下载 JSON 文件 |
| 13 | 点击"PDF"导出 | 下载 PDF（或 text fallback） |

- [ ] **Step 3: 检查浏览器 Console**

打开 DevTools → Console，确认：
- 0 个 JS error
- 无 404 请求
- 无 CORS 报错

如有异常，记录并修复。

- [ ] **Step 4: 如发现后端问题，修复**

常见可能问题及修复：

**问题 A**: SSE 事件格式不匹配 → 检查 `monitor_service.py` 的 `_sse()` 方法输出的格式是否被前端正确解析。

**问题 B**: 档案数据为空 → 确认 `stop_monitoring()` 是否正确将 buffer 数据写入 DB，`generate_archive()` 是否正确查询。

**问题 C**: 地图 marker 不移动 → 确认 `updateMapMarker()` 接收的 `data.lon`/`data.lat` 字段名与后端 SSE 事件字段一致。

---

## Round 2：代码健康

### Task 4: 清理 8 个孤儿组件

**Files:**
- Delete: 8 个 `.vue` 文件

- [ ] **Step 1: 确认未被引用**

逐个搜索确认每个组件在代码库中无任何引用：

```bash
# 对每个待删除组件执行（已确认 MonitorDashboard 现在被 TransportManager 使用，不删除）
grep -r "RouteForm" frontend/src/ --include="*.vue" --include="*.js"
grep -r "MapContainer" frontend/src/ --include="*.vue" --include="*.js"
grep -r "RouteResultPanel" frontend/src/ --include="*.vue" --include="*.js"
grep -r "SmartQA" frontend/src/ --include="*.vue" --include="*.js"
grep -r "StatusDashboard" frontend/src/ --include="*.vue" --include="*.js"
grep -r "TransportTracker" frontend/src/ --include="*.vue" --include="*.js"
grep -r "TransportArchive" frontend/src/ --include="*.vue" --include="*.js"
grep -r "VehicleProfileManager" frontend/src/ --include="*.vue" --include="*.js"
```

预期：每个搜索仅返回该组件自身的文件名（self-reference）或注释中的引用。

- [ ] **Step 2: 删除孤儿文件**

```bash
cd frontend/src/components
rm RouteForm.vue
rm MapContainer.vue
rm RouteResultPanel.vue
rm SmartQA.vue
rm StatusDashboard.vue
rm TransportTracker.vue
rm TransportArchive.vue
rm VehicleProfileManager.vue
```

- [ ] **Step 3: 验证构建**

```bash
cd frontend && npm run build
```
预期：构建成功，无 "module not found" 错误。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/
git commit -m "chore(frontend): 清理8个不再使用的孤儿组件"
```

---

### Task 5: 统一 API 调用 — TransportManager 使用 createOrder

**Files:**
- Modify: `frontend/src/components/TransportManager.vue`

- [ ] **Step 1: 替换 createTestOrder 中的 axios.post**

TransportManager 现有 `createTestOrder()` 中：
```javascript
const r = await axios.post(`${API_BASE}/api/v1/tracking/orders`, {
  route_data: routeData, vehicle_info: vehicleData, assessment_data: sharedStore.assessment || {}
})
```

替换为：
```javascript
const r = await createOrder({
  route_data: routeData,
  vehicle_info: vehicleData,
  assessment_data: sharedStore.assessment || {}
})
```

- [ ] **Step 2: 移除未使用的 axios import**

检查 `axios` 是否仍在其他地方使用。如果 `createTestOrder` 是唯一使用 `axios` 的地方，移除 `import axios from 'axios'` 以及 `const API_BASE = ...`。

TransportManager 中 `axios` 和 `API_BASE` 的用途检查：
- `loadOrders()` → 使用 `getOrders()` from `@/api/tracking` ✅
- `createTestOrder()` → 改用 `createOrder()` from `@/api/tracking` ✅
- 其他函数 → 均使用 API 模块 ✅

因此删除：
```javascript
import axios from 'axios'  // 删除
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:19876'  // 删除
```

- [ ] **Step 3: 验证构建**

```bash
cd frontend && npm run build
```
预期：构建成功，无 import 错误。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TransportManager.vue
git commit -m "refactor(TransportManager): createTestOrder改用API模块createOrder，移除裸axios调用"
```

---

### Task 6: 前端测试框架搭建

**Files:**
- Create: `frontend/vitest.config.js`
- Create: `frontend/src/components/__tests__/AiAssistant.spec.js`
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 vitest 依赖**

```bash
cd frontend
npm install -D vitest @vue/test-utils jsdom
```
预期：3 个包安装成功，添加到 devDependencies。

- [ ] **Step 2: 创建 frontend/vitest.config.js**

```javascript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.{js,jsx}'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 3: 添加 test script 到 package.json**

在 `package.json` 的 `scripts` 中添加：
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: 创建示例测试文件**

`frontend/src/components/__tests__/AiAssistant.spec.js`:

```javascript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AiAssistant from '../AiAssistant.vue'

describe('AiAssistant', () => {
  it('renders the floating button when collapsed', () => {
    const wrapper = mount(AiAssistant, {
      props: {
        routes: [],
        selectedRouteIndex: 0,
        vehicle: null,
      },
    })
    // 浮球按钮应存在
    const btn = wrapper.find('.ai-float-btn')
    expect(btn.exists()).toBe(true)
  })

  it('starts collapsed (panel hidden)', () => {
    const wrapper = mount(AiAssistant, {
      props: {
        routes: [],
        selectedRouteIndex: 0,
        vehicle: null,
      },
    })
    // 面板未展开时不应有输入框
    expect(wrapper.find('textarea, input[type="text"]').exists()).toBe(false)
  })
})
```

- [ ] **Step 5: 运行测试验证**

```bash
cd frontend && npm test
```
预期：2 tests pass。如果失败，检查 AiAssistant.vue 的 class 名是否匹配 `.ai-float-btn`。

- [ ] **Step 6: Commit**

```bash
git add frontend/vitest.config.js frontend/src/components/__tests__/ frontend/package.json frontend/package-lock.json
git commit -m "feat(test): 搭建前端测试框架vitest + @vue/test-utils + jsdom，添加AiAssistant示例测试"
```

---

## 完成验证

- [ ] 全量构建: `docker compose up -d --build` 3个服务启动成功
- [ ] 前端构建: `cd frontend && npm run build` 无错误
- [ ] 前端测试: `cd frontend && npm test` 全部通过
- [ ] E2E 流程: 规划→评估→发证→监控→停止→档案 完整走通
- [ ] Console: 0 errors

---

## 文件变更汇总

| 文件 | 操作 | 行数变化 |
|------|------|---------|
| `frontend/src/components/TransportManager.vue` | 修改 | -95 / +20 |
| `frontend/src/components/MonitorDashboard.vue` | 修改 | +40 |
| `frontend/src/components/RouteForm.vue` | 删除 | -320 |
| `frontend/src/components/MapContainer.vue` | 删除 | -200 |
| `frontend/src/components/RouteResultPanel.vue` | 删除 | -250 |
| `frontend/src/components/SmartQA.vue` | 删除 | -300 |
| `frontend/src/components/StatusDashboard.vue` | 删除 | -350 |
| `frontend/src/components/TransportTracker.vue` | 删除 | -200 |
| `frontend/src/components/TransportArchive.vue` | 删除 | -250 |
| `frontend/src/components/VehicleProfileManager.vue` | 删除 | -200 |
| `frontend/vitest.config.js` | 新建 | +17 |
| `frontend/src/components/__tests__/AiAssistant.spec.js` | 新建 | +30 |
| `frontend/package.json` | 修改 | +3 |
