/**
 * RoutePlanner 单元测试
 *
 * Quasar v2 的 server build 在 jsdom 中直接安装会失败（sd/Object.assign 内部报错），
 * 因此 mock 所有使用的 Quasar 组件并提供一个最小化的 installable plugin。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// ---------------------------------------------------------------------------
// Mock store
// ---------------------------------------------------------------------------
vi.mock('@/store/index.js', () => ({
  sharedStore: {
    vehicle: { length: 25, width: 3.5, height: 4.5, total_weight: 80, axis_weight: 15, axis_count: 6 },
    assessment: {},
    routes: [],
    selectedIdx: 0,
  },
  selectedRoute: vi.fn(() => null),
}))

// ---------------------------------------------------------------------------
// Mock axios
// ---------------------------------------------------------------------------
vi.mock('axios', () => ({
  default: {
    post: vi.fn().mockResolvedValue({ data: { code: 200, data: { routes: [] } } }),
  },
}))

// ---------------------------------------------------------------------------
// Mock child components
// ---------------------------------------------------------------------------
vi.mock('@/components/VehicleWizard.vue', () => ({
  default: {
    name: 'VehicleWizard',
    template: '<div class="mock-vehicle-wizard"></div>',
    emits: ['complete', 'close'],
  },
}))

vi.mock('@/components/RouteCompare.vue', () => ({
  default: {
    name: 'RouteCompare',
    template: '<div class="mock-route-compare"></div>',
    props: ['routes', 'vehicle'],
  },
}))

vi.mock('@/components/AssessmentResultPanel.vue', () => ({
  default: {
    name: 'AssessmentResultPanel',
    template: '<div class="mock-assessment-panel"></div>',
    props: ['assessment', 'assessing'],
  },
}))

// ---------------------------------------------------------------------------
// Mock Quasar — stub every component & plugin used in RoutePlanner
// ---------------------------------------------------------------------------
const $q = {
  notify: vi.fn(),
  screen: { width: 1920, height: 1080 },
  platform: { is: { desktop: true, mobile: false } },
}

// Specialized stubs that render label text so we can assert on it
const stubs = {
  'q-input': {
    name: 'q-input',
    template: '<div class="q-input">{{ label }}</div>',
    props: ['modelValue', 'label', 'dense', 'outlined', 'color', 'disable', 'clearable'],
    emits: ['update:modelValue'],
  },
  'q-btn': {
    name: 'q-btn',
    template: '<div class="q-btn">{{ label }}<slot /></div>',
    props: ['color', 'icon', 'label', 'flat', 'dense', 'size', 'loading', 'disable', 'round'],
    emits: ['click'],
  },
  'q-expansion-item': {
    name: 'q-expansion-item',
    template: '<div class="q-expansion-item"><slot /></div>',
    props: ['dense', 'label', 'headerClass'],
  },
  'q-list': {
    name: 'q-list',
    template: '<div class="q-list"><slot /></div>',
    props: ['dense', 'separator'],
  },
  'q-item': {
    name: 'q-item',
    template: '<div class="q-item"><slot /></div>',
    props: ['clickable', 'active'],
    emits: ['click'],
  },
  'q-item-section': {
    name: 'q-item-section',
    template: '<div class="q-item-section"><slot /></div>',
    props: ['side'],
  },
  'q-item-label': {
    name: 'q-item-label',
    template: '<div class="q-item-label"><slot /></div>',
    props: ['caption'],
  },
  'q-badge': {
    name: 'q-badge',
    template: '<div class="q-badge">{{ label }}</div>',
    props: ['color', 'label'],
  },
  'q-icon': {
    name: 'q-icon',
    template: '<div class="q-icon"></div>',
    props: ['name', 'color', 'size'],
  },
  'q-space': {
    name: 'q-space',
    template: '<div class="q-space"></div>',
  },
  'q-dialog': {
    name: 'q-dialog',
    template: '<div class="q-dialog"><slot /></div>',
    props: ['modelValue', 'maximized'],
    emits: ['update:modelValue'],
  },
  'q-card': {
    name: 'q-card',
    template: '<div class="q-card"><slot /></div>',
    props: ['style'],
  },
  'q-card-section': {
    name: 'q-card-section',
    template: '<div class="q-card-section"><slot /></div>',
  },
  'q-card-actions': {
    name: 'q-card-actions',
    template: '<div class="q-card-actions"><slot /></div>',
    props: ['align'],
  },
}

const QuasarPlugin = {
  install(app) {
    // Register specialized stubs for every Quasar component used in the template
    for (const [name, stub] of Object.entries(stubs)) {
      app.component(name, stub)
    }
    // Provide $q so useQuasar() works
    app.config.globalProperties.$q = $q
    app.provide('$q', $q)
  },
}

// ---------------------------------------------------------------------------
// SUT
// ---------------------------------------------------------------------------
import RoutePlanner from '@/components/RoutePlanner.vue'

function mountComponent(props = {}) {
  return mount(RoutePlanner, {
    global: {
      plugins: [QuasarPlugin],
      stubs: { ...stubs },
    },
    props: { ...props },
  })
}

// ---------------------------------------------------------------------------
// Test cases
// ---------------------------------------------------------------------------
describe('RoutePlanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始状态渲染起点输入区域（包含"起点"文本）', () => {
    const wrapper = mountComponent()
    expect(wrapper.html()).toContain('起点')
  })

  it('routes 数组初始为空', () => {
    const wrapper = mountComponent()
    expect(wrapper.vm.routeResults).toEqual([])
  })

  it('assessment 在评估前为 null', () => {
    const wrapper = mountComponent()
    expect(wrapper.vm.assessment).toBeNull()
  })
})
