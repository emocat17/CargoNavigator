<template>
  <div class="planner-root">
    <!-- ===== 全屏地图 ===== -->
    <div id="planner-map" class="planner-map"></div>

    <!-- ===== 左上浮动面板 ===== -->
    <div class="float-panel" :class="{ collapsed: panelCollapsed }">
      <div class="panel-header" @click="panelCollapsed = !panelCollapsed">
        <span class="text-subtitle2 text-weight-bold">{{ panelCollapsed ? '展开' : '路线规划' }}</span>
        <q-btn dense flat round :icon="panelCollapsed ? 'chevron_right' : 'expand_less'" size="sm" />
      </div>

      <div v-show="!panelCollapsed" class="panel-body">
        <!-- 起终点 -->
        <q-input dense outlined v-model="form.origin" label="起点" class="q-mb-sm" />
        <q-input dense outlined v-model="form.destination" label="终点" class="q-mb-sm" />

        <!-- 车辆快捷配置 -->
        <q-expansion-item dense label="车辆配置" header-class="text-caption">
          <div class="row q-col-gutter-xs">
            <div class="col-6"><q-input dense outlined v-model.number="vehicle.length" label="车长(m)" /></div>
            <div class="col-6"><q-input dense outlined v-model.number="vehicle.width" label="车宽(m)" /></div>
            <div class="col-6"><q-input dense outlined v-model.number="vehicle.height" label="车高(m)" /></div>
            <div class="col-6"><q-input dense outlined v-model.number="vehicle.total_weight" label="总重(t)" /></div>
          </div>
          <q-btn color="primary" icon="settings" label="完整配置" flat dense size="sm" class="q-mt-xs" @click="showVehicleWizard = true" />
        </q-expansion-item>

        <!-- 规划按钮 -->
        <q-btn color="primary" icon="route" label="开始规划" class="full-width q-mt-sm" @click="doPlanRoute" :loading="planning" />

        <!-- 路线结果 -->
        <div v-if="routeResults.length > 0" class="q-mt-sm">
          <div class="text-caption text-grey-6 q-mb-xs">共 {{ routeResults.length }} 条路线</div>
          <q-list dense separator>
            <q-item v-for="(r, i) in routeResults" :key="r.id" clickable :active="selectedIdx === i"
              @click="selectRoute(i)" class="route-item" v-ripple>
              <q-item-section>
                <q-item-label class="text-caption text-weight-bold">
                  方案{{ i + 1 }} · {{ (r.distance / 1000).toFixed(0) }}km · {{ fmtDuration(r.duration) }}
                </q-item-label>
                <q-item-label caption>
                  ¥{{ (r.toll_cost || 0).toFixed(0) }} · {{ r.strategy || '' }}
                  <span v-if="r.tags?.length" class="text-orange">🏷 {{ r.tags.join(',') }}</span>
                </q-item-label>
              </q-item-section>
              <q-item-section side v-if="r.score != null">
                <q-badge :color="scoreColor(r.score)" :label="r.score + '/10'" />
              </q-item-section>
            </q-item>
          </q-list>

          <!-- 操作按钮 -->
          <div class="row q-gutter-xs q-mt-sm">
            <q-btn color="secondary" icon="assessment" label="评估安全" dense size="sm" @click="doAssess" :loading="assessing" />
            <q-btn color="positive" icon="description" label="生成许可证" dense size="sm" @click="doGeneratePermit" :disable="!assessment" />
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 底部状态栏 ===== -->
    <div v-if="statusLine" class="status-bar">
      <span v-for="(s, i) in statusLine" :key="i" class="q-mr-md">
        <span :class="s.color">{{ s.icon }}</span> {{ s.label }}
      </span>
    </div>

    <!-- ===== 车辆配置弹窗 ===== -->
    <q-dialog v-model="showVehicleWizard" maximized>
      <VehicleWizard @save="onVehicleSaved" @cancel="showVehicleWizard = false" />
    </q-dialog>

    <!-- ===== 路线对比弹窗 ===== -->
    <q-dialog v-model="showCompare">
      <RouteCompare :routes="routeResults" :vehicle="vehicle" />
    </q-dialog>

    <!-- ===== 许可证预览弹窗 ===== -->
    <q-dialog v-model="showPermit">
      <q-card style="max-width: 700px;">
        <q-card-section>
          <div class="text-h6">许可证预览</div>
          <div v-if="permitData" class="q-mt-sm" style="max-height: 60vh; overflow-y: auto; white-space: pre-wrap; font-size: 12px;">
            {{ permitData }}
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="关闭" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import axios from 'axios'
import { sharedStore, selectedRoute } from '../store/index.js'
import VehicleWizard from './VehicleWizard.vue'
import RouteCompare from './RouteCompare.vue'

const $q = useQuasar()
const API = import.meta.env.VITE_API_BASE || 'http://localhost:19876'

const emit = defineEmits(['plan-route', 'select-route', 'view-transport'])
const props = defineProps({
  routes: { type: Array, default: () => [] },
  selectedRouteIndex: { type: Number, default: 0 },
})

// 表单
const form = reactive({ origin: '福建省三明厦钨新能源', destination: '福建省平潭跨境电商园' })
const vehicle = reactive({ length: 25, width: 3.5, height: 4.5, total_weight: 80, axis_weight: 15, axis_count: 6 })
const panelCollapsed = ref(false)
const planning = ref(false)
const assessing = ref(false)
const showVehicleWizard = ref(false)
const showCompare = ref(false)
const showPermit = ref(false)

// 结果
const routeResults = ref([])
const selectedIdx = ref(0)
const assessment = ref(null)
const permitData = ref(null)

// 地图
let mapInstance = null
let routePolylines = []
let markers = []

// 计算底部状态栏
const statusLine = computed(() => {
  const r = routeResults.value[selectedIdx.value]
  if (!r) return null
  const a = assessment.value
  const lines = [
    { icon: '🛣', label: `${(r.distance / 1000).toFixed(0)}km`, color: 'text-white' },
    { icon: '⏱', label: fmtDuration(r.duration), color: 'text-white' },
    { icon: '💰', label: `¥${(r.toll_cost || 0).toFixed(0)}`, color: 'text-white' },
  ]
  if (a) {
    const risk = a.data?.overall_assessment?.risk_level || a.riskLevel || '?'
    const score = a.data?.overall_assessment?.score ?? a.score ?? '?'
    lines.push({ icon: '⚠', label: `${risk} ${score}/10`, color: riskColor(risk) })
    const bridges = a.data?.route_compatibility?.structural_safety
    if (bridges) {
      const risky = bridges.high_risk_bridges || 0
      lines.push({ icon: '🌉', label: `${bridges.total_bridges}桥/${risky}风险`, color: risky > 0 ? 'text-orange' : 'text-green' })
    }
  }
  return lines
})

// ---- 地图 ----
function initMap() {
  if (mapInstance) return
  const load = () => {
    mapInstance = new window.AMap.Map('planner-map', {
      center: [118.3, 25.5],
      zoom: 8,
    })
  }
  if (window.AMap) { load() } else {
    const s = document.createElement('script')
    s.src = 'https://webapi.amap.com/maps?v=2.0&key=0625539f7941518573845dd16fe22316'
    s.onload = load
    document.head.appendChild(s)
  }
}

// ---- 路线规划 ----
async function doPlanRoute() {
  if (!form.origin || !form.destination) { $q.notify({ type: 'warning', message: '请输入起终点' }); return }
  planning.value = true
  try {
    const { data } = await axios.post(`${API}/api/v1/routes/plan`, {
      origin: form.origin, destination: form.destination, route_count: 3,
      vehicle: { length: vehicle.length, width: vehicle.width, height: vehicle.height, weight: vehicle.total_weight, axis_weight: vehicle.axis_weight, axis_count: vehicle.axis_count }
    })
    if (data.data?.routes?.length) {
      routeResults.value = data.data.routes
      selectedIdx.value = 0
      assessment.value = null
      // 保存到全局共享状态（供运输管理/数字档案使用）
      sharedStore.routes = data.data.routes.map(r => ({...r, _origin: form.origin, _destination: form.destination}))
      sharedStore.selectedIdx = 0
      sharedStore.vehicle = {...vehicle}
      await nextTick()
      drawRoutesOnMap()
    } else {
      $q.notify({ type: 'negative', message: '未找到路线' })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: '路线规划失败: ' + (e.response?.data?.detail || e.message) })
  }
  planning.value = false
}

function selectRoute(i) {
  selectedIdx.value = i
  sharedStore.selectedIdx = i
  drawRoutesOnMap()
}

function drawRoutesOnMap() {
  if (!mapInstance) return
  // 清除旧图层
  routePolylines.forEach(p => p.setMap(null)); routePolylines = []
  markers.forEach(m => m.setMap(null)); markers = []

  const colors = ['#2563eb', '#059669', '#ea580c']
  routeResults.value.forEach((r, i) => {
    if (!r.path_points) return
    const pts = r.path_points.split(';').filter(p => p).map(p => {
      const [lon, lat] = p.split(','); return [parseFloat(lon), parseFloat(lat)]
    })
    if (pts.length < 2) return
    const poly = new window.AMap.Polyline({
      path: pts,
      strokeColor: colors[i] || '#888',
      strokeWeight: i === selectedIdx.value ? 6 : 3,
      strokeOpacity: i === selectedIdx.value ? 1 : 0.5,
    })
    poly.setMap(mapInstance)
    routePolylines.push(poly)
  })
  // 聚焦选中路线
  if (routePolylines[selectedIdx.value]) mapInstance.setFitView([routePolylines[selectedIdx.value]])
}

// ---- 路线评估 ----
async function doAssess() {
  const r = routeResults.value[selectedIdx.value]
  if (!r) return
  assessing.value = true
  try {
    const { data } = await axios.post(`${API}/api/v1/routes/assess`, {
      route_data: { route_description: r.route_description || '', major_roads: r.major_roads || [],
        distance: r.distance || 0, duration: r.duration || 0, tunnel_count: r.tunnel_count || 0 },
      vehicle_info: { length: vehicle.length, width: vehicle.width, height: vehicle.height, total_weight: vehicle.total_weight, axis_weight: vehicle.axis_weight, axis_count: vehicle.axis_count }
    })
    assessment.value = data
    sharedStore.assessment = data
    if (data.code === 200) {
      addBridgeMarkers(data.data)
      $q.notify({ type: 'positive', message: `评估完成: ${data.data.overall_assessment?.risk_level || '?'} · ${data.data.overall_assessment?.score}/10` })
    }
  } catch (e) { $q.notify({ type: 'negative', message: '评估失败' }) }
  assessing.value = false
}

function addBridgeMarkers(assessData) {
  const bridges = assessData?.route_compatibility?.structural_safety?.bridge_details || []
  bridges.forEach(b => {
    if (!b.longitude || !b.latitude) return
    const color = { '安全通行': '#059669', '正常通行': '#059669', '建议限速': '#ea580c', '限速通行': '#ea580c', '条件通行': '#ea580c', '谨慎通行': '#dc2626', '不建议通行': '#dc2626' }
    const m = new window.AMap.Marker({
      position: [parseFloat(b.longitude), parseFloat(b.latitude)],
      title: `${b.station || ''} ${b.grade || ''}`,
      label: { content: b.station || '桥', direction: 'bottom' },
      icon: new window.AMap.Icon({
        size: new window.AMap.Size(20, 20),
        image: `data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="${(color[b.grade] || '#888').replace('#', '%23')}" opacity="0.8"/></svg>`,
        imageSize: new window.AMap.Size(20, 20),
      }),
    })
    m.setMap(mapInstance)
    markers.push(m)
  })
}

// ---- 许可证生成 ----
async function doGeneratePermit() {
  const r = routeResults.value[selectedIdx.value]
  if (!r) return
  try {
    const { data } = await axios.post(`${API}/api/v1/permit/preview`, {
      vehicle_info: { length: vehicle.length, width: vehicle.width, height: vehicle.height, total_weight: vehicle.total_weight, axis_count: vehicle.axis_count },
      cargo_info: { name: '大型设备', weight: vehicle.total_weight },
      applicant_info: { name: '测试物流公司', phone: '13800000000' },
      routes: [{ route_description: r.route_description || '', major_roads: r.major_roads || [], distance: r.distance || 0, duration: r.duration || 0 }]
    })
    if (data.code === 200) {
      permitData.value = data.data?.permit_text || JSON.stringify(data.data, null, 2)
      showPermit.value = true
    }
  } catch (e) { $q.notify({ type: 'negative', message: '生成失败' }) }
}

function onVehicleSaved(v) {
  Object.assign(vehicle, v)
  showVehicleWizard.value = false
}

function fmtDuration(s) { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h > 0 ? `${h}h${m}m` : `${m}min` }
function riskColor(level) { return ({ '低': 'text-green', '中': 'text-orange', '高': 'text-red', '极高': 'text-deep-orange' })[level] || 'text-grey' }
function scoreColor(s) { return s >= 7 ? 'green' : s >= 4 ? 'orange' : 'red' }

onMounted(() => { initMap() })
onBeforeUnmount(() => {
  if (mapInstance) { mapInstance.destroy(); mapInstance = null }
})
</script>

<style scoped>
.planner-root { position: relative; width: 100%; height: 100%; }
.planner-map { width: 100%; height: 100%; }

.float-panel {
  position: absolute; top: 12px; left: 12px;
  width: 340px; max-height: calc(100% - 60px);
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(12px);
  border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.25);
  overflow: hidden; z-index: 100;
  transition: width 0.2s;
}
.float-panel.collapsed { width: 60px; }
.panel-header {
  padding: 8px 12px; cursor: pointer;
  display: flex; justify-content: space-between; align-items: center;
  background: #f8fafc; border-bottom: 1px solid #e2e8f0;
}
.panel-body { padding: 10px 12px; overflow-y: auto; max-height: calc(100vh - 200px); }

.route-item { border-radius: 6px; margin: 2px 0; }
.route-item.q-item--active { background: #eff6ff; }

.status-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 36px; background: rgba(15,23,42,0.9);
  backdrop-filter: blur(8px);
  display: flex; align-items: center; padding: 0 16px;
  font-size: 12px; color: #94a3b8; z-index: 100;
}
</style>
