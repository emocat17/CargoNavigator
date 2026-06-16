/**
 * 全局共享状态 — 路线数据在三个页面间流转
 *
 * 数据流: RoutePlanner → sharedStore → TransportManager / DigitalArchive
 */
import { reactive } from 'vue'

export const sharedStore = reactive({
  // 规划的路线列表（含完整 Amap polyline、steps、tmcs 等）
  routes: [],
  // 当前选中路线索引
  selectedIdx: 0,
  // 当前车辆信息
  vehicle: {
    length: 25, width: 3.5, height: 4.5,
    total_weight: 80, axis_weight: 15, axis_count: 6,
  },
  // 路线评估结果
  assessment: null,
})

// 获取当前选中路线
export function selectedRoute() {
  return sharedStore.routes[sharedStore.selectedIdx] || null
}

// 获取指定路线的 polyline
export function getRoutePolyline(route) {
  if (!route) return ''
  return route.path_points || route._polyline || ''
}
