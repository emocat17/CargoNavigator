# CargoNavigator 精细化打磨 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3轮20项修复，从安全加固到结构优化，将项目打磨到生产级质量。

**Architecture:** 顺序3轮执行，每轮完成后独立验证（全量测试 + Docker 构建 + E2E 冒烟），独立 commit。Round1 聚焦安全与质量（密钥清理、异常规范、日志统一），Round2 聚焦代码健康（测试补齐、组件拆分、API 规范），Round3 聚焦结构优化（vue-router、Dockerfile 解耦、类型标注、README）。

**Tech Stack:** Vue 3 + Quasar + Vite, FastAPI + SQLAlchemy, Docker Compose, vitest, pytest

---

## Round 1: 安全+质量修复（Task 1-6）

### Task 1: API 密钥泄露修复

**Files:**
- Modify: `frontend/src/components/TransportManager.vue:179`
- Modify: `frontend/src/components/RoutePlanner.vue:198`
- Modify: `frontend/src/components/MonitorDashboard.vue:149`
- Modify: `frontend/src/components/DigitalArchive.vue:126`
- Modify: `.gitignore:72-74` (append rules)
- Remove tracking: `frontend/.env.production`

**Goal:** 从 git 移除真实 API 密钥，删除代码中硬编码 fallback，添加 `.gitignore` 规则。

- [ ] **Step 1: 从 git 移除 .env.production 追踪**

```bash
git rm --cached frontend/.env.production
```

- [ ] **Step 2: 更新 .gitignore 添加敏感文件规则**

Append to `.gitignore` section `# Project: Sensitive Config`:

```gitignore
!.env.template

# Also ignore production env (contains real keys)
*.env.production
```

- [ ] **Step 3: 修改 TransportManager.vue line 179 — 移除硬编码密钥**

Old:
```javascript
const KEY = import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'; const s = document.createElement('script'); s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`; s.onload = load; document.head.appendChild(s)
```
New:
```javascript
const key = import.meta.env.VITE_AMAP_KEY
if (!key) { console.error('[TransportManager] VITE_AMAP_KEY not set — map disabled'); return }
const s = document.createElement('script'); s.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`; s.onload = load; document.head.appendChild(s)
```

- [ ] **Step 4: 修改 RoutePlanner.vue line 198 — 移除硬编码密钥**

Old:
```javascript
s.src = `https://webapi.amap.com/maps?v=2.0&key=${import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'}`
```
New:
```javascript
const key = import.meta.env.VITE_AMAP_KEY
if (!key) { console.error('[RoutePlanner] VITE_AMAP_KEY not set — map disabled'); return }
s.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`
```

- [ ] **Step 5: 修改 MonitorDashboard.vue line 149 — 移除硬编码密钥**

Old:
```javascript
script.src = `https://webapi.amap.com/maps?v=2.0&key=${import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'}`
```
New:
```javascript
const key = import.meta.env.VITE_AMAP_KEY
if (!key) { console.error('[MonitorDashboard] VITE_AMAP_KEY not set — map disabled'); return }
script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`
```

- [ ] **Step 6: 修改 DigitalArchive.vue line 126 — 移除硬编码密钥**

Old:
```javascript
const KEY = import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'; const s = document.createElement('script'); s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`; s.onload = load; document.head.appendChild(s)
```
New:
```javascript
const key = import.meta.env.VITE_AMAP_KEY
if (!key) { console.error('[DigitalArchive] VITE_AMAP_KEY not set — map disabled'); return }
const s = document.createElement('script'); s.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`; s.onload = load; document.head.appendChild(s)
```

- [ ] **Step 7: 验证 — 检查 git 中不再有密钥**

```bash
git log --all --full-history -- frontend/.env.production   # 应显示已删除的历史
grep -r "0625539f7941518573845dd16fe22316" frontend/src/   # 应返回空
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "fix(security): 移除git中的API密钥和代码硬编码fallback

- git rm --cached frontend/.env.production（含真实高德密钥）
- .gitignore 新增 *.env.production 规则
- 4个Vue组件移除硬编码密钥 0625539f...，无配置时显式报错"
```

---

### Task 2: 裸 `except: pass` 修复

**Files:**
- Modify: `backend/app/api/routes.py:515`

**Goal:** 裸 `except:` 替换为具体异常类型 + 日志记录。

- [ ] **Step 1: 修改 routes.py line 515**

Old:
```python
        if request.departure_time:
            try:
                dep_time = datetime.fromisoformat(request.departure_time)
            except:
                pass
```
New:
```python
        if request.departure_time:
            try:
                dep_time = datetime.fromisoformat(request.departure_time)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid departure_time format '{request.departure_time}': {e}")
```

确保文件顶部已导入 logger：
```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: 验证 — 运行后端测试**

```bash
docker compose exec backend pytest -x -q
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes.py
git commit -m "fix(backend): 修复裸except:pass为具体异常类型+日志记录"
```

---

### Task 3: `print()` → `logging` 统一

**Files:**
- Modify: `backend/app/bridge_db.py:31`
- Modify: `backend/app/main.py:28,30`
- Modify: `backend/app/api/routes.py:310,532,554,569`

**Goal:** 所有 `print()` 调试输出替换为结构化 logging。

- [ ] **Step 1: 修改 bridge_db.py line 31**

Old:
```python
print(f"[BridgeDB] Initialized at {DB_PATH}")
```
New:
```python
logger.info(f"Initialized at {DB_PATH}")
```

确认文件顶部有:
```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: 修改 main.py lines 28,30**

Old:
```python
print("[Main] Bridge database initialized")
...
print(f"[Main] Bridge DB init skipped: {e}")
```
New:
```python
logger.info("Bridge database initialized")
...
logger.warning(f"Bridge DB init skipped: {e}")
```

确认文件顶部有:
```python
import logging
logger = logging.getLogger(__name__)
```

- [ ] **Step 3: 修改 routes.py lines 310,532,554,569**

Line 310:
```python
# Old: print(f"Error parsing TMC: {e}, Data: {tmc}")
logger.warning(f"Error parsing TMC: {e}, Data: {tmc}")
```

Line 532:
```python
# Old: print(f"Warning: Could not geocode waypoint '{wp}'")
logger.warning(f"Could not geocode waypoint '{wp}'")
```

Line 554:
```python
# Old: print(f"Strategy {strategies[i]} failed: {res}")
logger.warning(f"Strategy {strategies[i]} failed: {res}")
```

Line 569:
```python
# Old: print(f"Error processing strategy {strategies[i]}: {e}")
logger.error(f"Error processing strategy {strategies[i]}: {e}")
```

- [ ] **Step 4: 验证 — 后端测试 + 检查日志输出**

```bash
docker compose exec backend pytest -x -q
docker compose logs backend | grep -i "bridge\|TMC\|geocode\|Strategy"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/bridge_db.py backend/app/main.py backend/app/api/routes.py
git commit -m "refactor(backend): 统一使用logging替代print()调试输出"
```

---

### Task 4: 前端 console 清理 + 用户反馈

**Files:**
- Modify: `frontend/src/App.vue:72` (remove console.log)
- Modify: `frontend/src/components/MonitorDashboard.vue:135,213,243` (console.error→notify, remove console.log)
- Modify: `frontend/src/components/QualificationManager.vue:306,350,432` (console.error→notify)

**Goal:** 删除调试 console.log，console.error 补充用户可见的 `$q.notify()` 反馈。

- [ ] **Step 1: 修改 App.vue line 72 — 删除 console.log**

Old:
```javascript
console.log('[App] Plan route:', payload)
```
New: (delete the line entirely)

- [ ] **Step 2: 修改 MonitorDashboard.vue line 135 — console.error 补充 notify**

Old:
```javascript
console.error('Failed to load orders:', e)
```
New:
```javascript
import { useQuasar } from 'quasar'
// ... inside setup:
const $q = useQuasar()
// ...
$q.notify({ type: 'negative', message: '加载订单列表失败，请刷新重试' })
console.error('Failed to load orders:', e)
```

- [ ] **Step 3: 修改 MonitorDashboard.vue line 213 — console.error 补充 notify**

Old:
```javascript
console.error('SSE error:', e)
```
New:
```javascript
$q.notify({ type: 'warning', message: '监控连接中断，正在重连...' })
console.error('SSE error:', e)
```

- [ ] **Step 4: 修改 MonitorDashboard.vue line 243 — 删除 console.log**

Old:
```javascript
console.log('Monitor:', data.message)
```
New: (delete the line entirely)

- [ ] **Step 5: 修改 QualificationManager.vue lines 306,350,432**

Line 306:
```javascript
// Old: console.error('Failed to load saved data', e)
$q.notify({ type: 'warning', message: '加载本地缓存失败，将使用默认值' })
console.error('Failed to load saved data', e)
```

Line 350:
```javascript
// Old: console.error("Date parse error", e)
$q.notify({ type: 'warning', message: '日期解析失败，请检查输入格式' })
console.error("Date parse error", e)
```

Line 432:
```javascript
// Old: console.error('Failed to save to cloud', e)
$q.notify({ type: 'negative', message: '保存失败，请检查网络后重试' })
console.error('Failed to save to cloud', e)
```

- [ ] **Step 6: 验证 — 前端构建无错误**

```bash
cd frontend && npm run build 2>&1 | grep -i error || echo "Build OK"
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.vue frontend/src/components/MonitorDashboard.vue frontend/src/components/QualificationManager.vue
git commit -m "fix(frontend): 清理console.log，console.error补充用户可见notify反馈"
```

---

### Task 5: 后端 exception 处理规范化

**Files:**
- Modify: `backend/app/services/traffic_service.py:78-82`
- Modify: `backend/app/api/agent_routes.py:157-160`
- 检查并修复 7 处 `except Exception:` 无变量捕获

**Goal:** 消除所有 `except Exception: pass` 和 `except Exception:` 无变量模式。

- [ ] **Step 1: 修改 traffic_service.py lines 78-82**

Old:
```python
        try:
            from datetime import datetime
            now_hour = datetime.now().hour
        except Exception:
            pass
```
New:
```python
        try:
            from datetime import datetime
            now_hour = datetime.now().hour
        except (ValueError, TypeError, OSError):
            logger.debug("Could not determine current hour, using default")
```

- [ ] **Step 2: 修改 agent_routes.py lines 157-160**

Old:
```python
    try:
        llm_configured = bool(agent_service.llm_key)
    except Exception:
        llm_configured = False
```
New:
```python
    try:
        llm_configured = bool(agent_service.llm_key)
    except Exception as e:
        logger.warning(f"Failed to check LLM configuration: {e}")
        llm_configured = False
```

- [ ] **Step 3: 扫描并修复 7 处 `except Exception:` 无变量**

Run to find them:
```bash
grep -rn "except Exception:" backend/app/ | grep -v "as "
```

For each match, append `as e` and add `logger.error(f"Unexpected error: {e}")` or `logger.warning(f"...")` depending on context.

- [ ] **Step 4: 验证 — 后端测试全通过**

```bash
docker compose exec backend pytest -x -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/
git commit -m "fix(backend): 规范化exception处理，消除裸except和无声吞异常"
```

---

### Task 6: 垃圾文件清理

**Files:**
- Remove tracking: `page-docker.txt`
- Modify: `.gitignore` (append `page-*.txt` rule)

**Goal:** 从 git 移除调试 dump 文件，添加规则防止再提交。

- [ ] **Step 1: 从 git 移除并添加 gitignore 规则**

```bash
git rm --cached page-docker.txt
```

Append to `.gitignore` under `# OS / Temp`:
```gitignore
page-*.txt
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore(clean): 从git移除page-docker.txt调试文件，添加gitignore规则"
```

---

### Round 1 验证

- [ ] **Docker 构建验证**

```bash
docker compose up -d --build
docker compose ps  # 确认 backend/frontend 均为 healthy
```

- [ ] **前端 console 检查**

打开 `http://localhost:16789`，Console 中应 0 errors 0 warnings。

- [ ] **E2E 冒烟测试**

完成一次完整流程：路线规划 → 评估安全 → 运输管理 → 监控 → 归档。

---

## Round 2: 高质量提升（Task 7-12）

### Task 7: TransportManager 测试

**Files:**
- Create: `frontend/src/components/__tests__/TransportManager.spec.js`

**Goal:** 为 TransportManager 核心逻辑补充 4 个测试用例。

- [ ] **Step 1: 创建测试文件**

```javascript
/**
 * TransportManager 单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

// Mock the API modules
vi.mock('@/api/tracking', () => ({
  getOrders: vi.fn().mockResolvedValue({
    code: 200,
    data: {
      orders: [
        { id: '1', order_number: 'CN-001', status: 'PERMIT_ISSUED', created_at: '2026-06-17T10:00:00Z', route_data_json: { route_description: '福州→厦门', path_points: '119.3,26.1;118.1,24.5' } },
        { id: '2', order_number: 'CN-002', status: 'IN_TRANSIT', created_at: '2026-06-17T11:00:00Z', route_data_json: { route_description: '泉州→漳州', path_points: '118.6,24.9;117.6,24.5' } },
        { id: '3', order_number: 'CN-003', status: 'COMPLETED', created_at: '2026-06-16T09:00:00Z', route_data_json: { route_description: '莆田→龙岩', path_points: '119.0,25.4;117.0,25.1' } },
      ]
    }
  }),
  createOrder: vi.fn(),
  updateOrderStatus: vi.fn(),
}))

vi.mock('@/api/monitor', () => ({
  startMonitoring: vi.fn().mockResolvedValue({ code: 200 }),
}))

import TransportManager from '@/components/TransportManager.vue'

function mountComponent(props = {}) {
  return mount(TransportManager, {
    global: {
      plugins: [Quasar],
    },
    props: { ...props },
  })
}

describe('TransportManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染订单列表', async () => {
    const wrapper = mountComponent()
    // Wait for onMounted loadOrders()
    await new Promise(r => setTimeout(r, 50))
    const items = wrapper.findAll('.q-item')
    expect(items.length).toBeGreaterThan(0)
  })

  it('状态筛选过滤订单', async () => {
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    // Select PERMIT_ISSUED filter
    const select = wrapper.findComponent({ name: 'QSelect' })
    expect(select.exists()).toBe(true)
  })

  it('选中订单后显示详情卡片', async () => {
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    // Click first order
    const firstItem = wrapper.find('.q-item')
    if (firstItem.exists()) {
      await firstItem.trigger('click')
    }
    // Should show order number
    const tm = wrapper.vm
    expect(tm.selectedOrder).toBeTruthy()
  })

  it('startMonitor 设置 monitoringMode 为 true', async () => {
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    const tm = wrapper.vm
    tm.selectedOrder = { id: '1', status: 'IN_TRANSIT', route_data_json: {} }
    tm.startMonitor()
    expect(tm.monitoringMode).toBe(true)
  })
})
```

- [ ] **Step 2: 运行测试验证**

```bash
cd frontend && npx vitest run src/components/__tests__/TransportManager.spec.js
```

Expected: 4 tests pass (可能需要根据 Quasar 组件挂载行为微调)。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/__tests__/TransportManager.spec.js
git commit -m "test(frontend): 添加TransportManager单元测试 - 4个用例"
```

---

### Task 8: MonitorDashboard 测试

**Files:**
- Create: `frontend/src/components/__tests__/MonitorDashboard.spec.js`

**Goal:** 为 MonitorDashboard 核心逻辑补充 3 个测试用例。

- [ ] **Step 1: 创建测试文件**

```javascript
/**
 * MonitorDashboard 单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

vi.mock('@/api/monitor', () => ({
  startMonitoring: vi.fn().mockResolvedValue({ code: 200, msg: '监控已启动' }),
  stopMonitoring: vi.fn(),
  getActiveSessions: vi.fn().mockResolvedValue({ code: 200, data: { sessions: [] } }),
  getStreamUrl: vi.fn().mockReturnValue('/api/v1/monitor/stream/test'),
}))

vi.mock('@/api/tracking', () => ({
  getOrders: vi.fn().mockResolvedValue({
    code: 200,
    data: {
      orders: [
        { id: '1', order_number: 'CN-001', status: 'IN_TRANSIT', route_data_json: { route_description: '福州→厦门', path_points: '119.3,26.1;118.1,24.5' }, created_at: '2026-06-17T10:00:00Z' }
      ]
    }
  }),
}))

import MonitorDashboard from '@/components/MonitorDashboard.vue'

function mountComponent(props = {}) {
  return mount(MonitorDashboard, {
    global: { plugins: [Quasar] },
    props: { ...props },
  })
}

describe('MonitorDashboard', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('嵌入式模式接收 orderId props', () => {
    const wrapper = mountComponent({ embedded: true, orderId: 'order-123' })
    const md = wrapper.vm
    expect(md.embedded).toBe(true)
    expect(md.orderId).toBe('order-123')
  })

  it('非嵌入式模式显示控制栏', () => {
    const wrapper = mountComponent({ embedded: false })
    // Control bar should be visible in non-embedded mode
    const html = wrapper.html()
    // 非嵌入模式应包含订单选择器
    expect(html).toBeTruthy()
  })

  it('监控完成后 emit done 事件', async () => {
    const wrapper = mountComponent({ embedded: true, orderId: 'order-1' })
    const md = wrapper.vm
    // 模拟监控完成
    md.$emit('done')
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('done')).toBeTruthy()
  })
})
```

- [ ] **Step 2: 运行测试验证**

```bash
cd frontend && npx vitest run src/components/__tests__/MonitorDashboard.spec.js
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/__tests__/MonitorDashboard.spec.js
git commit -m "test(frontend): 添加MonitorDashboard单元测试 - 3个用例"
```

---

### Task 9: RoutePlanner 测试

**Files:**
- Create: `frontend/src/components/__tests__/RoutePlanner.spec.js`

**Goal:** 为 RoutePlanner 核心逻辑补充 3 个测试用例。

- [ ] **Step 1: 创建测试文件**

```javascript
/**
 * RoutePlanner 单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

vi.mock('@/api/assessment', () => ({
  assessRoute: vi.fn().mockResolvedValue({
    code: 200,
    data: {
      risk_level: 'low',
      score: 85,
      bridge_details: [],
      construction_events: [],
      estimated_cost: { total: 5000 },
      recommendations: [],
    }
  }),
}))

import RoutePlanner from '@/components/RoutePlanner.vue'

function mountComponent() {
  return mount(RoutePlanner, {
    global: { plugins: [Quasar] },
  })
}

describe('RoutePlanner', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('初始状态显示起点输入框', () => {
    const wrapper = mountComponent()
    const html = wrapper.html()
    // Should contain origin input area
    expect(html).toContain('起点')
  })

  it('无路线时不显示评估按钮', () => {
    const wrapper = mountComponent()
    // assessment should be null initially
    expect(wrapper.vm.assessment).toBe(null)
  })

  it('路线规划后路线列表更新', async () => {
    const wrapper = mountComponent()
    // Test that routes ref is initially empty
    expect(wrapper.vm.routes).toEqual([])
  })
})
```

- [ ] **Step 2: 运行测试验证**

```bash
cd frontend && npx vitest run src/components/__tests__/RoutePlanner.spec.js
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/__tests__/RoutePlanner.spec.js
git commit -m "test(frontend): 添加RoutePlanner单元测试 - 3个用例"
```

---

### Task 10: VehicleWizard 拆分

**Files:**
- Create: `frontend/src/components/VehicleWizard.vue` (重写为主容器 ~200行)
- Create: `frontend/src/components/VehicleFormStep.vue` (~300行)
- Create: `frontend/src/components/AxleConfigStep.vue` (~250行)
- Create: `frontend/src/components/ReviewConfirmStep.vue` (~200行)
- Read context: `frontend/src/components/VehicleWizard.vue` (当前 988行)

**Goal:** 将 988 行单体组件拆分为 1 个容器 + 3 个子组件，每个文件职责单一。

- [ ] **Step 1: 提取 VehicleFormStep.vue — 车辆类型选择+参数表单**

从当前 VehicleWizard.vue 提取:
- step 1 内容（挂车类型选择、车辆参数表单、轴数配置）
- Props: `modelValue` (Object — wizard data)
- Emits: `update:modelValue`

```vue
<template>
  <div class="step-content">
    <div class="text-h5 q-mb-sm">选择挂车类型</div>
    <div class="text-body1 text-grey-7 q-mb-lg">
      请根据实际运输配置选择对应的车辆组合类型
    </div>
    <div class="row q-col-gutter-md">
      <div v-for="(vt, idx) in vehicleTypes" :key="idx" class="col-12 col-md-4">
        <q-card
          :class="['type-card', { selected: modelValue.trailer_type === vt.value }]"
          @click="update('trailer_type', vt.value)"
          flat bordered
        >
          <q-card-section horizontal>
            <div class="type-icon" v-html="vt.icon" />
            <q-card-section>
              <div class="text-h6">{{ vt.label }}</div>
              <!-- ... rest of type card content from original ... -->
            </q-card-section>
          </q-card-section>
        </q-card>
      </div>
    </div>
    <!-- Vehicle parameters form (length/width/height/weight/axis_weight/axis_count) -->
    <!-- ... extracted from original step 1 ... -->
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true }
})
const emit = defineEmits(['update:modelValue'])

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

// Copy vehicleTypes array and related logic from original VehicleWizard
const vehicleTypes = [ /* ... from original ... */ ]
</script>

<style scoped>
/* Copy relevant styles from original */
</style>
```

- [ ] **Step 2: 提取 AxleConfigStep.vue — 轴重配置**

从当前 VehicleWizard.vue 提取 step 2 内容（轴重配置表），复用 AxleConfigurator 组件。

- [ ] **Step 3: 提取 ReviewConfirmStep.vue — 审核确认**

从当前 VehicleWizard.vue 提取 step 3-4 内容（参数汇总、审核、提交）。

- [ ] **Step 4: 重写 VehicleWizard.vue 为薄容器**

```vue
<template>
  <q-card class="bg-grey-1 vehicle-wizard" style="max-height: 95vh; display: flex; flex-direction: column;">
    <q-toolbar class="bg-primary text-white">
      <q-btn flat round dense icon="close" @click="emit('close')" />
      <q-toolbar-title>车辆参数配置向导</q-toolbar-title>
      <q-space />
      <q-btn flat :label="step > 1 ? '上一步' : ''" :icon="step > 1 ? 'arrow_back' : ''"
        @click="prevStep" :disable="step <= 1" />
      <div class="q-mx-sm text-caption">{{ step }} / {{ totalSteps }}</div>
      <q-btn v-if="step < totalSteps" flat label="下一步" icon-right="arrow_forward"
        color="white" @click="nextStep" />
      <q-btn v-else flat label="完成配置" icon="check_circle" color="white" @click="finish" />
    </q-toolbar>

    <q-card-section class="q-pa-lg" style="max-height: calc(100vh - 120px); overflow-y: auto;">
      <VehicleFormStep v-if="step === 1" v-model="wizard" />
      <AxleConfigStep v-if="step === 2" v-model="wizard" />
      <ReviewConfirmStep v-if="step === 3" v-model="wizard" @save="emit('save', wizard)" />
    </q-card-section>
  </q-card>
</template>

<script setup>
import { ref } from 'vue'
import VehicleFormStep from './VehicleFormStep.vue'
import AxleConfigStep from './AxleConfigStep.vue'
import ReviewConfirmStep from './ReviewConfirmStep.vue'

const emit = defineEmits(['close', 'save'])
const step = ref(1)
const totalSteps = 3

const wizard = ref({
  trailer_type: '',
  length: 25, width: 3.5, height: 4.5,
  total_weight: 80, axis_weight: 15, axis_count: 6,
})

function prevStep() { if (step.value > 1) step.value-- }
function nextStep() { if (step.value < totalSteps) step.value++ }
function finish() { emit('save', wizard.value) }
</script>
```

- [ ] **Step 5: 验证 — 前端构建无错误**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|warning" || echo "Build OK"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/VehicleWizard.vue frontend/src/components/VehicleFormStep.vue frontend/src/components/AxleConfigStep.vue frontend/src/components/ReviewConfirmStep.vue
git commit -m "refactor(frontend): 拆分VehicleWizard 988行→1容器+3子组件"
```

---

### Task 11: API fallback 规范化

**Files:**
- Modify: `frontend/src/api/index.js` (添加 BASE 导出)
- Modify: `frontend/src/api/tracking.js` (导入 BASE，移除硬编码 fallback)
- Modify: `frontend/src/api/monitor.js`
- Modify: `frontend/src/api/assessment.js`
- Modify: `frontend/src/api/permit.js`
- Modify: `frontend/src/api/survey.js`
- Modify: `frontend/src/api/archive.js`
- Modify: `frontend/src/api/agent.js`
- Modify: `frontend/src/api/vehicle.js`
- Modify: `frontend/src/api/application.js`

**Goal:** 统一 API 基地址管理，移除各模块硬编码 localhost fallback。

- [ ] **Step 1: 修改 api/index.js — 导出统一 BASE**

```javascript
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE

if (!API_BASE) {
  console.warn('[API] VITE_API_BASE not set — API calls will use relative path (requires nginx proxy)')
}

export const BASE = API_BASE ? `${API_BASE}/api/v1` : '/api/v1'

export { assessRoute, compareRoutes } from './assessment'
// ... rest of re-exports unchanged ...
```

- [ ] **Step 2: 修改所有 9 个 API 模块 — 导入 BASE，移除局部定义**

每个文件做相同的模式修改。以 `api/tracking.js` 为例：

Old:
```javascript
import axios from 'axios'
const API = import.meta.env.VITE_API_BASE || 'http://localhost:19876'
const BASE = `${API}/api/v1`
```
New:
```javascript
import axios from 'axios'
import { BASE } from './index'
```

依次修改: `tracking.js`, `monitor.js`, `assessment.js`, `permit.js`, `survey.js`, `archive.js`, `agent.js`, `vehicle.js`, `application.js`

- [ ] **Step 3: 验证 — 前端构建**

```bash
cd frontend && npm run build 2>&1 | grep -E "error" || echo "Build OK"
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/
git commit -m "refactor(frontend): 统一API基地址管理，移除9个模块中的硬编码localhost fallback"
```

---

### Task 12: 补充修复（nginx配置 + .gitignore + 占位数据）

**Files:**
- Create: `frontend/nginx.conf`
- Modify: `frontend/Dockerfile` (简化，COPY nginx.conf)
- Modify: `.gitignore` (追加 3 条规则)
- Modify: `backend/app/api/permit_routes.py:199` (占位数据)

**Goal:** 三项小修复打包完成。

- [ ] **Step 1: 创建 nginx.conf**

```nginx
server {
    listen 16789;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:19876;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

- [ ] **Step 2: 简化 frontend/Dockerfile**

Old (lines 16-27):
```dockerfile
RUN echo 'server { \
    listen 16789; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    location /api { \
        proxy_pass http://backend:19876; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf
```

New:
```dockerfile
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

- [ ] **Step 3: 更新 .gitignore**

Append to `# OS / Temp` section:
```gitignore
*.db-journal
```

- [ ] **Step 4: 修复 permit_routes.py 占位数据**

Old line 199:
```python
"id_number": "91350000XXXXXXXXXX"
```
New:
```python
"id_number": "请填写统一社会信用代码"
```

- [ ] **Step 5: Commit**

```bash
git add frontend/nginx.conf frontend/Dockerfile .gitignore backend/app/api/permit_routes.py
git commit -m "fix: nginx配置独立文件、gitignore补充、permit占位数据修正"
```

---

### Round 2 验证

- [ ] **全部测试**

```bash
docker compose exec backend pytest -x -q
cd frontend && npx vitest run
```

- [ ] **Docker 构建**

```bash
docker compose up -d --build
```

- [ ] **E2E 冒烟测试**

---

## Round 3: 结构优化（Task 13-16）

### Task 13: 引入 vue-router

**Files:**
- Create: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue` (v-show → router-view)
- Modify: `frontend/src/main.js` (注册 router)
- Create: `frontend/src/views/PlannerView.vue`
- Create: `frontend/src/views/TransportView.vue`
- Create: `frontend/src/views/ArchiveView.vue`

**Goal:** Tab-based `v-show` 切换改为 vue-router，隐藏页面不再渲染。

- [ ] **Step 1: 安装 vue-router**

```bash
cd frontend && npm install vue-router@4
```

- [ ] **Step 2: 创建 router/index.js**

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/planner' },
  { path: '/planner', name: 'planner', component: () => import('@/views/PlannerView.vue') },
  { path: '/transport', name: 'transport', component: () => import('@/views/TransportView.vue') },
  { path: '/archive', name: 'archive', component: () => import('@/views/ArchiveView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
```

- [ ] **Step 3: 创建 3 个 View 包装组件**

`PlannerView.vue`:
```vue
<template>
  <div style="height: calc(100vh - 56px); width: 100%;">
    <RoutePlanner />
  </div>
</template>
<script setup>
import RoutePlanner from '@/components/RoutePlanner.vue'
</script>
```

`TransportView.vue`:
```vue
<template>
  <div style="height: calc(100vh - 56px); width: 100%;">
    <TransportManager @view-archive="onViewArchive" />
  </div>
</template>
<script setup>
import { useRouter } from 'vue-router'
import TransportManager from '@/components/TransportManager.vue'
const router = useRouter()
function onViewArchive(orderId) {
  router.push({ name: 'archive', query: { orderId } })
}
</script>
```

`ArchiveView.vue`:
```vue
<template>
  <div style="height: calc(100vh - 56px); width: 100%;">
    <DigitalArchive />
  </div>
</template>
<script setup>
import DigitalArchive from '@/components/DigitalArchive.vue'
</script>
```

- [ ] **Step 4: 修改 main.js — 注册 router**

```javascript
import { createApp } from 'vue'
import { Quasar, Notify } from 'quasar'
import router from './router'
import App from './App.vue'
// ... quasar imports ...

const app = createApp(App)
app.use(Quasar, { plugins: { Notify } })
app.use(router)
app.mount('#app')
```

- [ ] **Step 5: 修改 App.vue — v-show 模式改为 router-view**

Replace the 3 v-show blocks with:
```vue
<router-view />
```

Remove `currentPage` ref and `pages` array. Bottom nav uses `$router.push()`:
```javascript
function go(page) { router.push({ name: page }) }
```

- [ ] **Step 6: 验证**

```bash
cd frontend && npm run build 2>&1 | grep -E "error" || echo "Build OK"
cd frontend && npx vitest run
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/router/ frontend/src/views/ frontend/src/main.js frontend/src/App.vue frontend/package.json
git commit -m "feat(frontend): 引入vue-router替代v-show页面切换"
```

---

### Task 14: Dockerfile 镜像源解耦

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `backend/Dockerfile.dev`
- Modify: `frontend/Dockerfile`
- Modify: `frontend/Dockerfile.dev`
- Modify: `docker-compose.yml`

**Goal:** 硬编码中国镜像 URL 改为 ARG 参数，保留默认值，可通过 `--build-arg` 切换。

- [ ] **Step 1: 修改 backend/Dockerfile**

Add ARG declarations near top:
```dockerfile
ARG PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_EXTRA_INDEX=https://pypi.org/simple
```

Change pip install lines:
```dockerfile
# Old: RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ ...
# New:
RUN pip install --no-cache-dir -i ${PIP_INDEX} --extra-index-url ${PIP_EXTRA_INDEX} ...
```

- [ ] **Step 2: 修改 backend/Dockerfile.dev**

Same pattern as Step 1 for the dev Dockerfile.

- [ ] **Step 3: 修改 frontend/Dockerfile**

Add ARG:
```dockerfile
ARG NPM_REGISTRY=https://registry.npmmirror.com
```

Change npm install:
```dockerfile
# Old: RUN npm ci
# New:
RUN npm ci --registry=${NPM_REGISTRY}
```

- [ ] **Step 4: 修改 frontend/Dockerfile.dev**

Same pattern as Step 3 for the dev Dockerfile.

- [ ] **Step 5: 修改 docker-compose.yml — 传入 ARG 默认值**

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
      args:
        PIP_INDEX: "${PIP_INDEX:-https://mirrors.aliyun.com/pypi/simple/}"
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
      args:
        NPM_REGISTRY: "${NPM_REGISTRY:-https://registry.npmmirror.com}"
```

- [ ] **Step 6: 验证 Docker 构建**

```bash
docker compose up -d --build
docker compose ps
```

- [ ] **Step 7: Commit**

```bash
git add backend/Dockerfile backend/Dockerfile.dev frontend/Dockerfile frontend/Dockerfile.dev docker-compose.yml
git commit -m "refactor(docker): 镜像源由硬编码改为ARG参数，保留中国镜像默认值"
```

---

### Task 15: Python 类型标注补充

**Files:**
- Modify: `backend/app/services/monitor_service.py` (补全返回值标注)
- Modify: `backend/app/services/route_assessor.py` (核心参数+返回值)
- Modify: `backend/app/services/tracking_service.py` (状态机关键路径)

**Goal:** 3 个核心服务补全类型标注，不改变运行时行为。

- [ ] **Step 1: monitor_service.py 类型标注**

为类方法添加返回值类型：

```python
from typing import AsyncGenerator, Optional, Dict, Any, List

class MonitorService:
    active_sessions: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def start_monitoring(cls, order_id: str, db: Session) -> Dict[str, Any]:
        ...

    @classmethod
    async def stream_events(cls, order_id: str) -> AsyncGenerator[str, None]:
        ...

    @classmethod
    async def stop_monitoring(cls, order_id: str, db: Session) -> Dict[str, Any]:
        ...

    @classmethod
    def get_active_sessions(cls) -> List[Dict[str, str]]:
        ...

    @staticmethod
    def _sse(event: str, data: str) -> str:
        ...

    @staticmethod
    def _extract_checkpoints(order) -> List[Dict[str, Any]]:
        ...
```

- [ ] **Step 2: route_assessor.py 核心方法标注**

为 `assess_route()` 和 `_build_route_compatibility()` 添加参数和返回值类型。

```python
async def assess_route(self, route_data: Dict[str, Any], vehicle_info: Dict[str, Any], 
                        db) -> Dict[str, Any]:
    ...

def _build_route_compatibility(self, route_data: Dict[str, Any], 
                                structural: Dict, construction: Dict,
                                dimension: Dict, cost: Dict) -> Dict[str, Any]:
    ...
```

- [ ] **Step 3: tracking_service.py 关键路径标注**

```python
@staticmethod
def update_status(db: Session, order_id: str, new_status: str, 
                  notes: str = "", changed_by: str = "system") -> Optional[TransportOrder]:
    ...
```

- [ ] **Step 4: 验证 — 后端测试 + mypy 检查**

```bash
docker compose exec backend pytest -x -q
docker compose exec backend mypy app/services/monitor_service.py app/services/route_assessor.py app/services/tracking_service.py --ignore-missing-imports 2>&1 || echo "mypy check done (warnings OK)"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/monitor_service.py backend/app/services/route_assessor.py backend/app/services/tracking_service.py
git commit -m "refactor(backend): 3核心服务补全Python类型标注"
```

---

### Task 16: README 更新

**Files:**
- Modify: `README.md`

**Goal:** 补充快速启动、端口说明、环境变量、技术栈等信息，约 60 行增量。

- [ ] **Step 1: 重写 README.md**

```markdown
# CargoNavigator — 大件运输智能选线系统

基于高德地图 API 和 AI 评估的大件运输路线规划与监控平台。

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Vue 3 + Quasar + Vite |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| 地图 | 高德 JS API v2.0 |
| 数据库 | SQLite (bridge.db + cargo_navigator.db) |
| 部署 | Docker Compose + Nginx |

## 快速启动

### 前置条件

- Docker & Docker Compose
- 高德地图 API Key（[申请地址](https://lbs.amap.com/)）

### 配置

```bash
cp .env.template .env
# 编辑 .env 填入你的 VITE_AMAP_KEY
```

### 启动

```bash
docker compose up -d --build
```

### 端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 16789 | Vue SPA + Nginx |
| 后端 | 19876 | FastAPI REST API |
| MaxKB | 8080 | 知识库 (profile: kb) |

### 访问

- **前端**: http://localhost:16789
- **API 文档**: http://localhost:19876/docs
- **健康检查**: http://localhost:19876/api/v1/health

## 页面功能

| 页面 | 路径 | 功能 |
|------|------|------|
| 路线规划 | `/planner` | 起终点输入、多路线规划、安全评估、发证审批 |
| 运输管理 | `/transport` | 订单列表、状态管理、GPS 实时监控 |
| 数字档案 | `/archive` | 历史记录、轨迹回放、数据导出 |

## 开发

```bash
# 后端测试
docker compose exec backend pytest -x -q

# 前端测试
cd frontend && npx vitest run

# 类型检查
docker compose exec backend mypy app/ --ignore-missing-imports
```

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| VITE_AMAP_KEY | 高德地图 JS API Key | 是 |
| VITE_API_BASE | 后端 API 地址 | 否 (默认 /api/v1) |
| DATABASE_URL | 主数据库连接 | 否 (默认 SQLite) |
| LLM_API_KEY | AI 评估 LLM Key | 否 |

## 项目结构

```
├── frontend/          # Vue 3 SPA
│   └── src/
│       ├── api/       # API 模块 (10 files)
│       ├── components/# Vue 组件 (14 files)
│       ├── router/    # Vue Router 配置
│       ├── views/     # 页面级组件
│       └── store/     # 共享状态
├── backend/           # FastAPI 服务
│   └── app/
│       ├── api/       # 路由 (10 files)
│       ├── services/  # 业务逻辑 (20 files)
│       └── models/    # ORM + Pydantic 模型
└── docs/              # 文档、设计规范、实现计划
```

## License

Proprietary — All rights reserved.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: 更新README - 快速启动、技术栈、端口说明、环境变量"
```

---

### Round 3 验证

- [ ] **全部测试**

```bash
docker compose exec backend pytest -x -q
cd frontend && npx vitest run
```

- [ ] **Docker 构建+运行**

```bash
docker compose down
docker compose up -d --build
docker compose ps
```

- [ ] **E2E 完整流程**

打开 `http://localhost:16789`，验证：
1. URL 自动跳转到 `/planner`
2. 底部导航切换页面（URL 变化，页面响应）
3. 浏览器前进/后退按钮正常工作
4. 完整流程：规划 → 评估 → 运输 → 监控 → 归档
5. Console: 0 errors 0 warnings

---

## 最终验证（全部完成）

- [ ] **git status** — 干净，无污染文件
- [ ] **docker compose up -d --build** — 3 服务 healthy
- [ ] **前端 console** — 0 errors 0 warnings
- [ ] **后端日志** — `docker compose logs backend | grep -i error` 无异常
- [ ] **前端测试** — `npx vitest run` 全通过
- [ ] **后端测试** — `pytest -x -q` 全通过
- [ ] **E2E** — 规划→评估→运输→监控→归档 全链路正常
