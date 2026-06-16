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
            <template v-if="selectedOrder.status === 'IN_TRANSIT' && !isMonitoring">
              <q-btn color="primary" icon="monitor_heart" label="启动监控" dense size="sm" @click="startMonitor" />
            </template>
            <template v-if="isMonitoring">
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

          <!-- 监控信息覆盖 -->
          <div v-if="isMonitoring && currentGps" class="monitor-overlay">
            <q-card flat class="q-pa-xs" style="background:rgba(0,0,0,0.75);color:#fff;">
              <div class="text-caption">📍 {{ currentGps.lon }}, {{ currentGps.lat }} | 🏃 {{ currentGps.speed }}km/h | 🎯 剩余{{ currentGps.distance_remaining }}km</div>
              <div class="row q-gutter-xs q-mt-xs text-caption">
                <span class="text-green">✅ 检查点: {{ checkpoints.length }}</span>
                <span class="text-orange">⚠ 告警: {{ alerts.length }}</span>
              </div>
            </q-card>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import axios from 'axios'
import { getOrders, updateOrderStatus } from '@/api/tracking'
import { startMonitoring, getStreamUrl, stopMonitoring } from '@/api/monitor'

const $q = useQuasar()
const emit = defineEmits(['view-archive'])
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:19876'

const filterStatus = ref(null)
const statusOptions = ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'PERMIT_ISSUED', 'IN_TRANSIT', 'COMPLETED'].map(s => ({ label: s, value: s }))
const orders = ref([])
const selectedOrder = ref(null)
const actionLoading = ref(false)
const isMonitoring = ref(false)
const currentGps = ref(null)
const checkpoints = ref([])
const alerts = ref([])
let transportMap = null
let vehicleMarker = null
let routeLine = null
let abortCtrl = null

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
    const r = await axios.post(`${API_BASE}/api/v1/tracking/orders`, {
      route_data: { path_points: '119.296,26.074;119.30,26.08;118.089,24.48', route_description: '福州→厦门·G15沈海高速', major_roads: ['G15沈海高速'], distance: 280000, duration: 12000 },
      vehicle_info: { length: 25, width: 3.5, height: 4.5, total_weight: 80, axis_weight: 15, axis_count: 6 },
      assessment_data: {}
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
    const s = document.createElement('script'); s.src = 'https://webapi.amap.com/maps?v=2.0&key=0625539f7941518573845dd16fe22316'; s.onload = load; document.head.appendChild(s)
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
  try { await updateOrderStatus(selectedOrder.value.id, 'IN_TRANSIT'); selectedOrder.value.status = 'IN_TRANSIT'; $q.notify({ type: 'positive', message: '运输已开始' }) } catch (e) { $q.notify({ type: 'negative', message: '操作失败' }) }
  actionLoading.value = false
}

async function startMonitor() {
  if (!selectedOrder.value) return
  try {
    const r = await startMonitoring(selectedOrder.value.id)
    if (r.code === 200) {
      isMonitoring.value = true; alerts.value = []; checkpoints.value = []
      connectSSE(selectedOrder.value.id)
    }
  } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || '启动失败' }) }
}

function connectSSE(orderId) {
  if (abortCtrl) abortCtrl.abort(); abortCtrl = new AbortController()
  fetch(getStreamUrl(orderId), { signal: abortCtrl.signal }).then(async resp => {
    const reader = resp.body.getReader(); const decoder = new TextDecoder(); let buf = ''
    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buf += decoder.decode(value, { stream: true })
      for (const frame of buf.split('\n\n')) {
        if (!frame.trim()) continue
        const lines = frame.split('\n'); let et = '', d = ''
        for (const l of lines) { if (l.startsWith('event: ')) et = l.slice(7).trim(); else if (l.startsWith('data: ')) d = l.slice(6) }
        try { d = JSON.parse(d) } catch { /* raw string */ }
        if (et === 'gps') { currentGps.value = d; updateVehicleMarker(d) }
        else if (et === 'checkpoint') checkpoints.value.push({ ...d, passed: true })
        else if (et === 'alert') alerts.value.unshift(d)
        else if (et === 'done') { isMonitoring.value = false; selectedOrder.value.status = 'COMPLETED'; $q.notify({ type: 'positive', message: '监控完成' }) }
      }
      buf = ''
      await nextTick()
    }
  }).catch(e => { if (e.name !== 'AbortError') console.error('SSE:', e); isMonitoring.value = false })
}

function updateVehicleMarker(pos) {
  if (!transportMap) return
  const lnglat = [pos.lon, pos.lat]
  if (vehicleMarker) vehicleMarker.setPosition(lnglat)
  else { vehicleMarker = new window.AMap.Marker({ position: lnglat, icon: new window.AMap.Icon({ size: new window.AMap.Size(32, 32), image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png', imageSize: new window.AMap.Size(32, 32) }) }); vehicleMarker.setMap(transportMap) }
  transportMap.setCenter(lnglat)
}

async function stopMonitor() {
  if (!selectedOrder.value) return
  try { if (abortCtrl) { abortCtrl.abort(); abortCtrl = null }; const r = await stopMonitoring(selectedOrder.value.id); isMonitoring.value = false; selectedOrder.value.status = 'COMPLETED'; $q.notify({ type: 'positive', message: `归档: ${r.data?.gps_points_saved || 0} GPS点` }) } catch (e) { $q.notify({ type: 'negative', message: '停止失败' }) }
}

function statusColor(s) { return ({ DRAFT: 'grey', SUBMITTED: 'blue', UNDER_REVIEW: 'orange', APPROVED: 'green', PERMIT_ISSUED: 'teal', IN_TRANSIT: 'primary', COMPLETED: 'green', REJECTED: 'red', CANCELLED: 'grey' })[s] || 'grey' }
function fmtDate(d) { if (!d) return ''; return new Date(d).toLocaleDateString('zh-CN') }

onMounted(() => { loadOrders() })
onBeforeUnmount(() => { if (abortCtrl) abortCtrl.abort(); if (transportMap) transportMap.destroy() })
</script>

<style scoped>
.tm-root { width: 100%; height: 100%; }
.tm-sidebar { width: 320px; height: 100%; border-right: 1px solid #e2e8f0; background: #fff; }
#transport-map { width: 100%; height: 100%; }
.monitor-overlay { position: absolute; top: 8px; left: 8px; right: 8px; z-index: 100; }
</style>
