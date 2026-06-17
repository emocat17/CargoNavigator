/**
 * TransportManager 单元测试
 *
 * Quasar v2 的 server build 在 jsdom 中直接安装会失败（sd/Object.assign 内部报错），
 * 因此 mock 所有使用的 Quasar 组件并提供一个最小化的 installable plugin。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// ---------------------------------------------------------------------------
// Mock API modules
// ---------------------------------------------------------------------------
vi.mock('@/api/tracking', () => ({
  getOrders: vi.fn().mockResolvedValue({
    code: 200,
    data: {
      orders: [
        { id: '1', order_number: 'CN-001', status: 'PERMIT_ISSUED', created_at: '2026-06-17T10:00:00Z', route_data_json: { route_description: '福州→厦门', path_points: '119.3,26.1;118.1,24.5' } },
        { id: '2', order_number: 'CN-002', status: 'IN_TRANSIT', created_at: '2026-06-17T11:00:00Z', route_data_json: { route_description: '泉州→漳州', path_points: '118.6,24.9;117.6,24.5' } },
      ]
    }
  }),
  createOrder: vi.fn(),
  updateOrderStatus: vi.fn(),
}))

vi.mock('@/api/monitor', () => ({
  startMonitoring: vi.fn().mockResolvedValue({ code: 200 }),
}))

// ---------------------------------------------------------------------------
// Mock store
// ---------------------------------------------------------------------------
vi.mock('@/store/index.js', () => ({
  sharedStore: {
    vehicle: { length: 25, width: 3.5, height: 4.5, total_weight: 80, axis_weight: 15, axis_count: 6 },
    assessment: {}
  },
  selectedRoute: vi.fn(() => null),
  getRoutePolyline: vi.fn(() => ''),
}))

// ---------------------------------------------------------------------------
// Mock MonitorDashboard child component
// ---------------------------------------------------------------------------
vi.mock('@/components/MonitorDashboard.vue', () => ({
  default: {
    name: 'MonitorDashboard',
    template: '<div class="mock-monitor"></div>',
    props: { embedded: Boolean, orderId: String },
    emits: ['done'],
  },
}))

// ---------------------------------------------------------------------------
// Mock Quasar — stub every component & plugin used in TransportManager
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
    props: ['modelValue', 'options', 'label', 'color', 'icon', 'dense', 'size', 'flat', 'loading', 'clickable', 'active', 'clearable', 'separator', 'caption'],
    emits: ['click', 'update:modelValue'],
  }
}

const QuasarPlugin = {
  install(app) {
    // Register stubs for every Quasar component used in the template
    for (const name of ['q-select', 'q-scroll-area', 'q-list', 'q-item', 'q-item-section', 'q-item-label', 'q-badge', 'q-icon', 'q-btn', 'q-space']) {
      app.component(name, makeStub(name))
    }
    // Provide $q so useQuasar() works
    app.config.globalProperties.$q = $q
    app.provide('$q', $q)
  },
}

// ---------------------------------------------------------------------------
// SUT
// ---------------------------------------------------------------------------
import TransportManager from '@/components/TransportManager.vue'

function mountComponent(props = {}) {
  return mount(TransportManager, {
    global: {
      plugins: [QuasarPlugin],
      stubs: {
        // Keep the stubs for any components we might have missed
        'q-select': makeStub('q-select'),
        'q-scroll-area': makeStub('q-scroll-area'),
        'q-list': makeStub('q-list'),
        'q-item': makeStub('q-item'),
        'q-item-section': makeStub('q-item-section'),
        'q-item-label': makeStub('q-item-label'),
        'q-badge': makeStub('q-badge'),
        'q-icon': makeStub('q-icon'),
        'q-btn': makeStub('q-btn'),
        'q-space': makeStub('q-space'),
      },
    },
    props: { ...props },
  })
}

// ---------------------------------------------------------------------------
// Test cases
// ---------------------------------------------------------------------------
describe('TransportManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('挂载后加载订单列表', async () => {
    const wrapper = mountComponent()
    // Wait for onMounted → loadOrders async call
    await new Promise(r => setTimeout(r, 50))
    expect(wrapper.vm.orders.length).toBeGreaterThan(0)
  })

  it('选中订单后更新 selectedOrder', async () => {
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    wrapper.vm.selectOrder({
      id: '1',
      order_number: 'CN-001',
      status: 'PERMIT_ISSUED',
      route_data_json: { route_description: '福州→厦门', path_points: '119.3,26.1;118.1,24.5' }
    })
    expect(wrapper.vm.selectedOrder).toBeTruthy()
    expect(wrapper.vm.selectedOrder.order_number).toBe('CN-001')
  })

  it('startMonitor 设置 monitoringMode 为 true', async () => {
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    wrapper.vm.selectedOrder = { id: '1', status: 'IN_TRANSIT', route_data_json: {} }
    wrapper.vm.startMonitor()
    expect(wrapper.vm.monitoringMode).toBe(true)
  })

  it('onMonitorDone 重置 monitoringMode 并刷新订单', async () => {
    const wrapper = mountComponent()
    await new Promise(r => setTimeout(r, 50))
    const { getOrders } = await import('@/api/tracking')
    wrapper.vm.selectedOrder = { id: '1', status: 'IN_TRANSIT', route_data_json: {} }
    wrapper.vm.monitoringMode = true
    wrapper.vm.onMonitorDone()
    expect(wrapper.vm.monitoringMode).toBe(false)
    expect(wrapper.vm.selectedOrder.status).toBe('COMPLETED')
    expect(getOrders).toHaveBeenCalled()
  })
})
