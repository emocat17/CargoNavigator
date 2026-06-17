/**
 * MonitorDashboard 单元测试
 *
 * Quasar v2 的 server build 在 jsdom 中直接安装会失败（sd/Object.assign 内部报错），
 * 因此 mock 所有使用的 Quasar 组件并提供一个最小化的 installable plugin。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

// ---------------------------------------------------------------------------
// Mock API modules
// ---------------------------------------------------------------------------
vi.mock('@/api/tracking', () => ({
  getOrders: vi.fn().mockResolvedValue({
    code: 200,
    data: {
      orders: [
        { id: '1', order_number: 'CN-001', status: 'IN_TRANSIT', created_at: '2026-06-17T10:00:00Z', route_data_json: { route_description: '福州→厦门', path_points: '119.3,26.1;118.1,24.5' } },
      ]
    }
  }),
}))

vi.mock('@/api/monitor', () => ({
  startMonitoring: vi.fn().mockResolvedValue({ code: 200 }),
  stopMonitoring: vi.fn().mockResolvedValue({ code: 200, data: { gps_points_saved: 0, checkpoints_saved: 0 } }),
  getActiveSessions: vi.fn().mockResolvedValue({ code: 200, data: [] }),
  getStreamUrl: vi.fn().mockReturnValue('/api/monitor/stream/1'),
}))

// ---------------------------------------------------------------------------
// Mock Quasar — stub every component & plugin used in MonitorDashboard
// ---------------------------------------------------------------------------
const $q = {
  notify: vi.fn(),
  screen: { width: 1920, height: 1080 },
  platform: { is: { desktop: true, mobile: false } },
}

// Minimal generic stub for any Quasar component
function makeStub(name) {
  return {
    name,
    template: `<div class="${name}"><slot /></div>`,
    props: ['modelValue', 'options', 'label', 'color', 'icon', 'dense', 'size', 'flat', 'loading', 'clickable', 'active', 'clearable', 'separator', 'caption', 'disable', 'outlined', 'bordered', 'avatar'],
    emits: ['click', 'update:modelValue'],
  }
}

const QuasarPlugin = {
  install(app) {
    // Register stubs for every Quasar component used in the template
    for (const name of ['q-select', 'q-btn', 'q-space', 'q-spinner-dots', 'q-card', 'q-card-section', 'q-list', 'q-item', 'q-item-section', 'q-item-label', 'q-icon']) {
      app.component(name, makeStub(name))
    }
    // Provide $q so useQuasar() works
    app.config.globalProperties.$q = $q
    app.provide('$q', $q)
  },
}

// ---------------------------------------------------------------------------
// SSE fetch helpers
// ---------------------------------------------------------------------------
function mockFetchDone() {
  return vi.fn().mockResolvedValue({
    ok: true,
    body: {
      getReader: () => ({
        read: () => Promise.resolve({ done: true, value: undefined })
      })
    }
  })
}

const realFetch = global.fetch

// ---------------------------------------------------------------------------
// SUT
// ---------------------------------------------------------------------------
import MonitorDashboard from '@/components/MonitorDashboard.vue'

function mountComponent(props = {}) {
  return mount(MonitorDashboard, {
    global: {
      plugins: [QuasarPlugin],
      stubs: {
        'q-select': makeStub('q-select'),
        'q-btn': makeStub('q-btn'),
        'q-space': makeStub('q-space'),
        'q-spinner-dots': makeStub('q-spinner-dots'),
        'q-card': makeStub('q-card'),
        'q-card-section': makeStub('q-card-section'),
        'q-list': makeStub('q-list'),
        'q-item': makeStub('q-item'),
        'q-item-section': makeStub('q-item-section'),
        'q-item-label': makeStub('q-item-label'),
        'q-icon': makeStub('q-icon'),
      },
    },
    props: { ...props },
  })
}

// ---------------------------------------------------------------------------
// Test cases
// ---------------------------------------------------------------------------
describe('MonitorDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    global.fetch = realFetch
  })

  it('嵌入式模式正确接收 orderId 属性', () => {
    global.fetch = mockFetchDone()
    const wrapper = mountComponent({ embedded: true, orderId: '123' })
    expect(wrapper.props('embedded')).toBe(true)
    expect(wrapper.props('orderId')).toBe('123')
  })

  it('非嵌入模式渲染控制栏（订单选择器可见）', async () => {
    global.fetch = vi.fn()
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    const select = wrapper.findComponent({ name: 'q-select' })
    expect(select.exists()).toBe(true)
  })

  it('监控完成时触发 done 事件', async () => {
    global.fetch = mockFetchDone()
    const wrapper = mountComponent({ embedded: true, orderId: '1' })
    // Wait for onMounted → loadOrders → startMonitor → connectSSE → fetch resolve → reader done → emit
    await new Promise(r => setTimeout(r, 200))
    expect(wrapper.emitted('done')).toBeTruthy()
    expect(wrapper.emitted('done').length).toBe(1)
  })
})
