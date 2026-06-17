<template>
  <div class="tm-root row">
    <!-- 左侧订单列表 -->
    <div class="tm-sidebar column">
      <div class="q-pa-sm bg-grey-2">
        <div class="text-subtitle2 text-weight-bold">运输单</div>
        <q-select dense outlined v-model="filterStatus" :options="statusOptions" label="状态筛选" clearable class="q-mt-xs" @update:model-value="loadOrders" />
      </div>
      <q-scroll-area class="col" style="flex:1;">
        <q-list dense separator>
          <q-item v-for="o in filteredOrders" :key="o.id" clickable :active="selectedOrder?.id === o.id" @click="selectOrder(o)" v-ripple>
            <q-item-section>
              <q-item-label class="text-caption text-weight-bold">{{ o.order_number }}</q-item-label>
              <q-item-label caption>
                {{ o.route_data_json?.route_description || '无路线描述' }}
              </q-item-label>
              <div class="row q-gutter-xs q-mt-xs">
                <q-badge :color="statusColor(o.status)" :label="o.status" />
                <span class="text-caption text-grey-6">{{ fmtDate(o.created_at) }}</span>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-if="orders.length === 0" class="text-center text-grey-5 q-pa-lg">
          <q-icon name="inbox" size="2rem" /><div class="text-caption q-mt-sm">暂无运输单</div>
          <q-btn color="primary" label="创建测试订单" dense flat size="sm" class="q-mt-sm" @click="createTestOrder" />
        </div>
      </q-scroll-area>
      <div class="q-pa-xs bg-grey-2 text-center">
        <q-btn color="primary" icon="add" label="新建运输单" dense size="sm" @click="createTestOrder" />
      </div>
    </div>

    <!-- 右侧详情/地图 -->
    <div class="col column" style="flex:1;">
      <div v-if="!selectedOrder" class="flex flex-center text-grey-5" style="height:100%;">
        <div class="text-center">
          <q-icon name="local_shipping" size="4rem" />
          <div class="text-h6 q-mt-sm">选择一个运输单</div>
          <div class="text-caption">查看详情或启动监控</div>
        </div>
      </div>

      <template v-else>
        <!-- Monitoring mode: full-screen MonitorDashboard -->
        <div v-if="monitoringMode" class="col column" style="flex:1;">
          <MonitorDashboard
            embedded
            :order-id="selectedOrder.id"
            @done="onMonitorDone"
          />
        </div>

        <!-- Normal mode: detail card + small map -->
        <template v-else>
          <!-- Detail card -->
          <div class="q-pa-sm bg-white" style="border-bottom:1px solid #e2e8f0;">
            <div class="row items-center">
              <span class="text-h6">{{ selectedOrder.order_number }}</span>
              <q-badge :color="statusColor(selectedOrder.status)" :label="selectedOrder.status" class="q-ml-sm" />
              <q-space />
              <!-- Action buttons -->
              <template v-if="selectedOrder.status === 'PERMIT_ISSUED'">
                <q-btn color="positive" icon="play_arrow" label="开始运输" dense size="sm" @click="startTransport" :loading="actionLoading" />
              </template>
              <template v-if="selectedOrder.status === 'IN_TRANSIT' && !monitoringMode">
                <q-btn color="primary" icon="monitor_heart" label="启动监控" dense size="sm" @click="startMonitor" />
              </template>
              <template v-if="selectedOrder.status === 'COMPLETED'">
                <q-btn color="secondary" icon="archive" label="查看档案" dense size="sm" @click="$emit('view-archive', selectedOrder.id)" />
              </template>
            </div>
            <!-- Status timeline -->
            <div class="row q-gutter-xs q-mt-xs text-caption">
              <span v-for="(s, i) in statusTimeline" :key="i" :class="s.done ? 'text-green' : 'text-grey-4'">
                {{ s.label }} {{ i < statusTimeline.length - 1 ? '→' : '' }}
              </span>
            </div>
          </div>

          <!-- Map area -->
          <div class="col" style="flex:1; position:relative;">
            <div id="transport-map" style="width:100%;height:100%;"></div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import axios from 'axios'
import { sharedStore, selectedRoute, getRoutePolyline } from '../store/index.js'
import MonitorDashboard from './MonitorDashboard.vue'
import { createOrder, getOrders, updateOrderStatus } from '@/api/tracking'
import { startMonitoring } from '@/api/monitor'

const $q = useQuasar()
const emit = defineEmits(['view-archive'])
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:19876'

const filterStatus = ref(null)
const statusOptions = ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'PERMIT_ISSUED', 'IN_TRANSIT', 'COMPLETED'].map(s => ({ label: s, value: s }))
const orders = ref([])
const selectedOrder = ref(null)
const actionLoading = ref(false)
const monitoringMode = ref(false)
let transportMap = null
let routeLine = null

const filteredOrders = computed(() => {
  if (!filterStatus.value) return orders.value
  return orders.value.filter(o => o.status === filterStatus.value)
})

const statusTimeline = ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'PERMIT_ISSUED', 'IN_TRANSIT', 'COMPLETED']

async function loadOrders() {
  try { const r = await getOrders(0, 500); if (r.code === 200) orders.value = r.data?.orders || [] } catch (e) { /* */ }
}

async function createTestOrder() {
  actionLoading.value = true
  try {
    // 使用共享 store 中的真实路线数据（含完整 Amap polyline）
    const route = selectedRoute()
    const routeData = route ? {
      path_points: getRoutePolyline(route) || '',
      route_description: route.route_description || `${route._origin || '?'}→${route._destination || '?'}`,
      major_roads: route.major_roads || [],
      distance: route.distance || 0,
      duration: route.duration || 0,
      tunnel_count: route.tunnel_count || 0,
      toll_cost: route.toll_cost || 0,
      traffic_condition: route.traffic_condition || '',
      passed_cities: route.passed_cities || [],
    } : {
      path_points: '119.296,26.074;119.30,26.08;118.089,24.48',
      route_description: '福州→厦门',
      major_roads: ['G15沈海高速'],
      distance: 280000, duration: 12000,
    }
    const vehicleData = {
      length: sharedStore.vehicle.length || 25,
      width: sharedStore.vehicle.width || 3.5,
      height: sharedStore.vehicle.height || 4.5,
      total_weight: sharedStore.vehicle.total_weight || 80,
      axis_weight: sharedStore.vehicle.axis_weight || 15,
      axis_count: sharedStore.vehicle.axis_count || 6,
    }
    const r = await axios.post(`${API_BASE}/api/v1/tracking/orders`, {
      route_data: routeData, vehicle_info: vehicleData, assessment_data: sharedStore.assessment || {}
    })
    if (r.data?.code === 200) {
      const oid = r.data.data.id
      for (const s of ['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'PERMIT_ISSUED']) {
        try { await updateOrderStatus(oid, s) } catch { /* skip invalid transitions */ }
      }
      $q.notify({ type: 'positive', message: `创建成功: ${r.data.data.order_number}` })
      await loadOrders()
    }
  } catch (e) { $q.notify({ type: 'negative', message: '创建失败' }) }
  actionLoading.value = false
}



function selectOrder(o) {
  selectedOrder.value = o
  nextTick(() => { initMap(); drawRouteOnMap(o) })
}

function initMap() {
  if (transportMap) return
  const load = () => {
    transportMap = new window.AMap.Map('transport-map', { center: [118.3, 25.5], zoom: 8 })
  }
  if (window.AMap) load(); else {
    const KEY = import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'; const s = document.createElement('script'); s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`; s.onload = load; document.head.appendChild(s)
  }
}

function drawRouteOnMap(o) {
  if (!transportMap) return
  if (routeLine) routeLine.setMap(null)
  const pts = (o.route_data_json?.path_points || '').split(';').filter(p => p).map(p => { const [lon, lat] = p.split(','); return [parseFloat(lon), parseFloat(lat)] })
  if (pts.length >= 2) { routeLine = new window.AMap.Polyline({ path: pts, strokeColor: '#2563eb', strokeWeight: 4 }); routeLine.setMap(transportMap); transportMap.setFitView([routeLine]) }
}

async function startTransport() {
  if (!selectedOrder.value) return
  actionLoading.value = true
  try { await updateOrderStatus(selectedOrder.value.id, 'IN_TRANSIT', '开始运输'); selectedOrder.value.status = 'IN_TRANSIT'; $q.notify({ type: 'positive', message: '运输已开始' }) } catch (e) { $q.notify({ type: 'negative', message: '操作失败' }) }
  actionLoading.value = false
}

async function startMonitor() {
  if (!selectedOrder.value) return
  monitoringMode.value = true
  $q.notify({ type: 'info', message: '正在连接监控...' })
}

function onMonitorDone() {
  monitoringMode.value = false
  if (selectedOrder.value) {
    selectedOrder.value.status = 'COMPLETED'
  }
  loadOrders()
}

function statusColor(s) { return ({ DRAFT: 'grey', SUBMITTED: 'blue', UNDER_REVIEW: 'orange', APPROVED: 'green', PERMIT_ISSUED: 'teal', IN_TRANSIT: 'primary', COMPLETED: 'green', REJECTED: 'red', CANCELLED: 'grey' })[s] || 'grey' }
function fmtDate(d) { if (!d) return ''; return new Date(d).toLocaleDateString('zh-CN') }

onMounted(() => { loadOrders() })
onBeforeUnmount(() => { if (transportMap) transportMap.destroy() })
</script>

<style scoped>
.tm-root { width: 100%; height: 100%; }
.tm-sidebar { width: 320px; height: 100%; border-right: 1px solid #e2e8f0; background: #fff; }
#transport-map { width: 100%; height: 100%; }
</style>
