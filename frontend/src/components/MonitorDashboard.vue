<template>
  <div class="q-pa-md column" :style="embedded ? 'height:100%;' : 'height: calc(100vh - 120px);'">
    <!-- Control Bar -->
    <div class="row q-mb-sm q-col-gutter-sm items-center">
      <div v-if="!embedded" class="col-auto">
        <q-select v-model="selectedOrderId" :options="orderOptions" label="选择运输单"
          style="width: 280px;" dense outlined @update:model-value="onOrderSelected" />
      </div>
      <div v-if="!embedded" class="col-auto">
        <q-btn color="primary" icon="play_arrow" label="开始监控" @click="startMonitor"
          :disable="!selectedOrderId || isMonitoring" dense />
      </div>
      <div class="col-auto">
        <q-btn color="red" icon="stop" label="停止监控" @click="stopMonitor"
          :disable="!isMonitoring" dense />
      </div>
      <q-space />
      <div class="col-auto text-caption" v-if="isMonitoring">
        <q-spinner-dots size="sm" color="primary" /> 监控中
      </div>
    </div>

    <!-- Info Bar -->
    <div v-if="currentGps" class="row q-mb-sm q-col-gutter-sm text-caption bg-blue-1 q-pa-xs rounded-borders">
      <div class="col-auto">&#x1F4CD; {{ currentGps.lon }}, {{ currentGps.lat }}</div>
      <div class="col-auto">&#x1F3C3; {{ currentGps.speed }} km/h</div>
      <div class="col-auto">&#x1F9ED; {{ currentGps.heading }}&deg;</div>
      <div class="col-auto">&#x1F3AF; 剩余 {{ currentGps.distance_remaining }} km</div>
    </div>

    <!-- Main Content: Map + Sidebar -->
    <div class="row col" style="flex:1; min-height:0;">
      <!-- Map (2/3 width) -->
      <div class="col-8 q-pr-sm" style="height:100%;">
        <div id="monitor-map" style="width:100%; height:100%; min-height:400px; border:1px solid #ddd; border-radius:8px;"></div>
      </div>

      <!-- Sidebar (1/3 width) -->
      <div class="col-4 column" style="height:100%;">
        <!-- Checkpoint List -->
        <q-card flat bordered class="q-mb-sm" style="flex:1; overflow-y:auto;">
          <q-card-section class="q-pa-sm bg-grey-2">
            <div class="text-subtitle2">检查点</div>
          </q-card-section>
          <q-list dense>
            <q-item v-for="(cp, idx) in checkpoints" :key="idx" dense class="q-pa-xs">
              <q-item-section avatar>
                <q-icon :name="cp.passed ? 'check_circle' : 'radio_button_unchecked'"
                  :color="cp.passed ? 'green' : 'grey'" size="xs" />
              </q-item-section>
              <q-item-section>
                <div class="text-caption">{{ cp.station }} <span class="text-grey-7">{{ cp.type }}</span></div>
                <div class="text-caption text-grey-7" v-if="cp.passed">{{ cp.passed_at }}</div>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-if="checkpoints.length === 0" class="text-center text-grey-6 q-pa-sm text-caption">
            暂无检查点数据
          </div>
        </q-card>

        <!-- Alert Panel -->
        <q-card flat bordered style="flex:1; overflow-y:auto;">
          <q-card-section class="q-pa-sm bg-grey-2">
            <div class="text-subtitle2">告警 ({{ alerts.length }})</div>
          </q-card-section>
          <q-list dense>
            <q-item v-for="(al, idx) in alerts" :key="idx" dense class="q-pa-xs">
              <q-item-section avatar>
                <q-icon :name="alertIcon(al.severity)" :color="alertColor(al.severity)" size="xs" />
              </q-item-section>
              <q-item-section>
                <div class="text-caption text-weight-medium">{{ al.message }}</div>
                <div class="text-caption text-grey-7">{{ al.timestamp }}</div>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-if="alerts.length === 0 && isMonitoring" class="text-center text-grey-6 q-pa-sm text-caption">
            <q-icon name="check" color="green" size="sm" /> 运行正常
          </div>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { getOrders } from '@/api/tracking'
import { startMonitoring, getStreamUrl, stopMonitoring } from '@/api/monitor'

const $q = useQuasar()
const props = defineProps({
  embedded: Boolean,
  orderId: [String, Number]
})
const emit = defineEmits(['view-archive', 'done'])

const selectedOrderId = ref(null)
const orderOptions = ref([])
const isMonitoring = ref(false)
const currentGps = ref(null)
const checkpoints = ref([])
const alerts = ref([])
let mapInstance = null
let vehicleMarker = null
let abortController = null

onMounted(async () => {
  await loadOrders()
  await nextTick()
  initMap()
  if (props.embedded && props.orderId) {
    selectedOrderId.value = props.orderId
    await nextTick()
    await startMonitor()
  }
})

onBeforeUnmount(() => {
  if (abortController) abortController.abort()
  if (mapInstance) mapInstance.destroy()
})

async function loadOrders() {
  try {
    const res = await getOrders(0, 500)
    if (res.code === 200) {
      orderOptions.value = (res.data.orders || [])
        .filter(o => ['PERMIT_ISSUED', 'IN_TRANSIT', 'COMPLETED'].includes(o.status))
        .map(o => ({ label: `${o.order_number} (${o.status})`, value: o.id }))
    }
  } catch (e) {
    console.error('Failed to load orders:', e)
  }
}

function initMap() {
  const loadAmap = () => {
    mapInstance = new window.AMap.Map('monitor-map', {
      center: [118.089, 24.480],
      zoom: 9,
    })
  }

  const key = import.meta.env.VITE_AMAP_KEY
  if (!key) { console.error('[MonitorDashboard] VITE_AMAP_KEY not set - map disabled'); return }
  if (!window.AMap) {
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`
    script.onload = loadAmap
    document.head.appendChild(script)
  } else {
    loadAmap()
  }
}

function onOrderSelected() {
  // Placeholder — could preload route onto map
}

async function startMonitor() {
  if (!selectedOrderId.value) return
  try {
    const res = await startMonitoring(selectedOrderId.value)
    if (res.code === 200) {
      isMonitoring.value = true
      alerts.value = []
      checkpoints.value = []
      connectSSE(selectedOrderId.value)
      $q.notify({ type: 'positive', message: '监控已启动' })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || '启动监控失败' })
  }
}

function connectSSE(orderId) {
  if (abortController) abortController.abort()
  abortController = new AbortController()

  fetch(getStreamUrl(orderId), { signal: abortController.signal }).then(async (resp) => {
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop()

      for (const frame of events) {
        if (!frame.trim()) continue
        const lines = frame.split('\n')
        let eventType = '', dataStr = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim()
          else if (line.startsWith('data: ')) dataStr = line.slice(6)
        }
        if (!eventType || !dataStr) continue

        let parsed
        try { parsed = JSON.parse(dataStr) } catch { parsed = dataStr }
        handleSSEEvent(eventType, parsed)
      }
    }
    isMonitoring.value = false
    if (props.embedded) emit('done')
  }).catch((e) => {
    if (e.name !== 'AbortError') {
      console.error('SSE error:', e)
      $q.notify({ type: 'negative', message: 'SSE连接断开' })
    }
    isMonitoring.value = false
    if (props.embedded) emit('done')
  })
}

function handleSSEEvent(eventType, data) {
  switch (eventType) {
    case 'gps':
      currentGps.value = data
      updateMapMarker(data)
      break
    case 'checkpoint':
      checkpoints.value.push({
        station: data.station,
        type: data.checkpoint_type || data.type,
        highway: data.highway,
        passed: true,
        passed_at: data.passed_at,
      })
      break
    case 'alert':
      alerts.value.unshift({ ...data, timestamp: data.timestamp || new Date().toISOString() })
      if (data.severity === 'high' || data.severity === 'critical') {
        $q.notify({ type: 'warning', message: data.message, position: 'top-right', timeout: 4000 })
      }
      break
    case 'status':
      console.log('Monitor:', data.message)
      break
    case 'error':
      $q.notify({ type: 'negative', message: data.message || '监控错误' })
      break
    case 'done':
      isMonitoring.value = false
      $q.notify({ type: 'positive', message: '监控已完成' })
      emit('done')
      break
  }
}

function updateMapMarker(data) {
  if (!mapInstance) return
  const lnglat = [data.lon, data.lat]
  if (vehicleMarker) {
    vehicleMarker.setPosition(lnglat)
  } else {
    vehicleMarker = new window.AMap.Marker({
      position: lnglat,
      icon: new window.AMap.Icon({
        size: new window.AMap.Size(32, 32),
        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
        imageSize: new window.AMap.Size(32, 32),
      }),
    })
    mapInstance.add(vehicleMarker)
  }
  mapInstance.setCenter(lnglat)
}

async function stopMonitor() {
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
      emit('done')
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || '停止失败' })
  }
}

function alertIcon(severity) {
  return { low: 'info', medium: 'warning', high: 'error', critical: 'report' }[severity] || 'warning'
}
function alertColor(severity) {
  return { low: 'grey', medium: 'orange', high: 'red', critical: 'deep-orange' }[severity] || 'grey'
}
</script>
