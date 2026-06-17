<template>
  <div class="q-pa-md column" style="height: calc(100vh - 120px);">
    <div class="text-h6 q-mb-sm">运输数字档案</div>

    <div class="row q-mb-sm q-col-gutter-sm items-center">
      <div class="col-auto">
        <q-select v-model="selectedOrderId" :options="orderOptions" label="选择运输单"
          style="width: 280px;" dense outlined @update:model-value="loadArchive" />
      </div>
      <q-space />
      <div class="col-auto" v-if="archive">
        <q-btn color="primary" icon="download" label="导出JSON" @click="exportArchive('json')" dense flat />
        <q-btn color="secondary" icon="picture_as_pdf" label="导出PDF" @click="exportArchive('pdf')" dense flat class="q-ml-sm" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!archive" class="text-center text-grey-6 q-mt-lg">
      <q-icon name="inventory_2" size="3rem" />
      <p>选择一个已完成的运输单查看数字档案</p>
    </div>

    <template v-else>
      <!-- Summary Cards -->
      <div class="row q-col-gutter-sm q-mb-sm">
        <div class="col-3">
          <q-card flat bordered class="text-center q-pa-sm">
            <div class="text-caption text-grey-6">GPS轨迹点</div>
            <div class="text-h6">{{ archive.gps_summary.total_points }}</div>
          </q-card>
        </div>
        <div class="col-3">
          <q-card flat bordered class="text-center q-pa-sm">
            <div class="text-caption text-grey-6">平均速度</div>
            <div class="text-h6">{{ archive.gps_summary.avg_speed }} km/h</div>
          </q-card>
        </div>
        <div class="col-3">
          <q-card flat bordered class="text-center q-pa-sm">
            <div class="text-caption text-grey-6">检查点通过</div>
            <div class="text-h6">{{ archive.checkpoints.length }}</div>
          </q-card>
        </div>
        <div class="col-3">
          <q-card flat bordered class="text-center q-pa-sm">
            <div class="text-caption text-grey-6">异常事件</div>
            <div class="text-h6" :class="archive.alerts.length > 0 ? 'text-red' : 'text-green'">
              {{ archive.alerts.length }}
            </div>
          </q-card>
        </div>
      </div>

      <q-separator class="q-mb-sm" />

      <!-- Tab: Timeline vs Replay -->
      <q-tabs v-model="viewMode" dense class="text-grey" active-color="primary" indicator-color="primary">
        <q-tab name="timeline" label="事件时间线" />
        <q-tab name="replay" label="轨迹回放" />
      </q-tabs>
      <q-separator class="q-mb-sm" />

      <q-tab-panels v-model="viewMode" class="col" style="flex:1; min-height:0;">
        <!-- Timeline View -->
        <q-tab-panel name="timeline" class="q-pa-none" style="height:100%; overflow-y:auto;">
          <q-timeline color="primary">
            <q-timeline-entry v-for="(evt, idx) in timelineEvents" :key="idx"
              :icon="evt.icon" :color="evt.color" :title="evt.title" :subtitle="evt.time">
              <div class="text-caption">{{ evt.detail }}</div>
            </q-timeline-entry>
          </q-timeline>
          <div v-if="timelineEvents.length === 0" class="text-center text-grey-6 q-pa-md">
            暂无事件记录
          </div>
        </q-tab-panel>

        <!-- Replay View -->
        <q-tab-panel name="replay" class="q-pa-none" style="height:100%;">
          <div id="archive-replay-map" style="width:100%; height:100%; min-height:350px; border:1px solid #ddd; border-radius:8px;"></div>
        </q-tab-panel>
      </q-tab-panels>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import { useQuasar } from 'quasar'
import { getOrders } from '@/api/tracking'
import { getArchive, getExportUrl } from '@/api/archive'

const $q = useQuasar()
const selectedOrderId = ref(null)
const orderOptions = ref([])
const archive = ref(null)
const viewMode = ref('timeline')
let replayMap = null

onBeforeUnmount(() => {
  if (replayMap) replayMap.destroy()
})

// Load order list on mount
;(async () => {
  try {
    const res = await getOrders(0, 500)
    if (res.code === 200) {
      orderOptions.value = (res.data.orders || [])
        .filter(o => o.status === 'COMPLETED')
        .map(o => ({ label: o.order_number, value: o.id }))
    }
  } catch (e) { console.error('Failed to load orders:', e) }
})()

async function loadArchive(orderId) {
  if (!orderId) return
  try {
    const res = await getArchive(orderId)
    if (res.code === 200) {
      archive.value = res.data
      await nextTick()
      if (viewMode.value === 'replay') initReplayMap()
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || '加载档案失败' })
  }
}

const timelineEvents = computed(() => {
  if (!archive.value) return []
  const events = []

  // Order timeline entries
  for (const entry of (archive.value.timeline || [])) {
    events.push({
      icon: entry.is_completed ? 'check_circle' : 'radio_button_unchecked',
      color: entry.is_completed ? 'green' : 'grey',
      title: entry.label || entry.status,
      time: entry.changed_at || '',
      detail: entry.change_reason || '',
    })
  }

  // Checkpoint events
  for (const cp of (archive.value.checkpoints || [])) {
    events.push({
      icon: 'check_circle',
      color: 'blue',
      title: `通过检查点: ${cp.station} (${cp.type})`,
      time: cp.passed_at || '',
      detail: cp.highway || '',
    })
  }

  // Alert events
  const severityColor = { low: 'grey', medium: 'orange', high: 'red', critical: 'deep-orange' }
  for (const al of (archive.value.alerts || [])) {
    events.push({
      icon: 'warning',
      color: severityColor[al.severity] || 'orange',
      title: `[${al.severity}] ${al.message}`,
      time: al.timestamp || '',
      detail: '',
    })
  }

  events.sort((a, b) => (a.time || '').localeCompare(b.time || ''))
  return events
})

function initReplayMap() {
  const gps = archive.value?.gps_track || []
  const center = gps.length > 0
    ? [parseFloat(gps[0].longitude), parseFloat(gps[0].latitude)]
    : [118.089, 24.480]

  const loadMap = () => {
    replayMap = new window.AMap.Map('archive-replay-map', { center, zoom: 11 })

    if (gps.length > 1) {
      const path = gps.map(p => [parseFloat(p.longitude), parseFloat(p.latitude)])
      const polyline = new window.AMap.Polyline({
        path, strokeColor: '#2196F3', strokeWeight: 4,
      })
      replayMap.add(polyline)
      replayMap.setFitView()
    }

    for (const cp of (archive.value?.checkpoints || [])) {
      if (cp.longitude && cp.latitude) {
        new window.AMap.Marker({
          position: [parseFloat(cp.longitude), parseFloat(cp.latitude)],
          title: cp.station,
          label: { content: cp.station, direction: 'top' },
        }).setMap(replayMap)
      }
    }
  }

  if (!window.AMap) {
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'}`
    script.onload = loadMap
    document.head.appendChild(script)
  } else {
    loadMap()
  }
}

function exportArchive(format) {
  if (!selectedOrderId.value) return
  window.open(getExportUrl(selectedOrderId.value, format), '_blank')
}

defineExpose({ loadArchive })
</script>
