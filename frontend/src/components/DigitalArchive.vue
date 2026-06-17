<template>
  <div class="da-root row">
    <!-- 左侧档案列表 -->
    <div class="da-sidebar column">
      <div class="q-pa-sm bg-grey-2"><div class="text-subtitle2 text-weight-bold">已完成运输单</div></div>
      <q-scroll-area class="col">
        <q-list dense separator>
          <q-item v-for="o in orders" :key="o.id" clickable :active="selectedId === o.id" @click="loadArchive(o.id)" v-ripple>
            <q-item-section>
              <q-item-label class="text-caption text-weight-bold">{{ o.order_number }}</q-item-label>
              <q-item-label caption>{{ fmtDate(o.completed_at || o.updated_at) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-if="orders.length === 0" class="text-center text-grey-5 q-pa-lg">
          <q-icon name="archive" size="2rem" /><div class="text-caption q-mt-sm">暂无已完成运输单</div>
        </div>
      </q-scroll-area>
    </div>

    <!-- 右侧档案详情 -->
    <div class="col column" style="flex:1;">
      <div v-if="!archive" class="flex flex-center text-grey-5" style="height:100%;">
        <div class="text-center"><q-icon name="archive" size="4rem" /><div class="text-h6 q-mt-sm">选择一个运输单</div></div>
      </div>

      <template v-else>
        <!-- 摘要栏 -->
        <div class="q-pa-sm bg-white row q-col-gutter-sm" style="border-bottom:1px solid #e2e8f0;">
          <div class="col-3 text-center"><div class="text-caption text-grey-6">GPS点</div><div class="text-h6 text-primary">{{ archive.gps_summary?.total_points || 0 }}</div></div>
          <div class="col-3 text-center"><div class="text-caption text-grey-6">均速</div><div class="text-h6">{{ archive.gps_summary?.avg_speed || 0 }} km/h</div></div>
          <div class="col-3 text-center"><div class="text-caption text-grey-6">检查点</div><div class="text-h6">{{ archive.checkpoints?.length || 0 }}</div></div>
          <div class="col-3 text-center"><div class="text-caption text-grey-6">告警</div><div class="text-h6" :class="archive.alerts?.length > 0 ? 'text-red' : ''">{{ archive.alerts?.length || 0 }}</div></div>
          <div class="col-12 text-right"><q-btn dense flat color="primary" icon="download" label="JSON" @click="exportIt('json')" /><q-btn dense flat color="secondary" icon="picture_as_pdf" label="PDF" @click="exportIt('pdf')" class="q-ml-sm" /></div>
        </div>

        <!-- Tab切换 -->
        <q-tabs v-model="tab" dense class="bg-grey-1">
          <q-tab name="timeline" label="事件时间线" />
          <q-tab name="replay" label="轨迹回放" />
          <q-tab name="checkpoints" label="检查点明细" />
        </q-tabs>

        <!-- 内容区 -->
        <div class="col" style="flex:1; overflow: auto;">
          <!-- 时间线 -->
          <q-tab-panel v-if="tab === 'timeline'" class="q-pa-sm">
            <q-timeline dense color="primary">
              <q-timeline-entry v-for="(e, i) in timelineItems" :key="i" :icon="e.icon" :color="e.color" :title="e.title" :subtitle="e.time" />
            </q-timeline>
          </q-tab-panel>

          <!-- 轨迹回放地图 -->
          <q-tab-panel v-if="tab === 'replay'" class="q-pa-none" style="height:100%;">
            <div id="replay-map" style="width:100%; height:100%; min-height:400px;"></div>
          </q-tab-panel>

          <!-- 检查点表格 -->
          <q-tab-panel v-if="tab === 'checkpoints'" class="q-pa-sm">
            <q-table dense flat :rows="archive.checkpoints || []" :columns="cpColumns" row-key="station" hide-pagination />
          </q-tab-panel>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { getOrders } from '@/api/tracking'
import { getArchive, getExportUrl } from '@/api/archive'

const selectedId = ref(null)
const orders = ref([])
const archive = ref(null)
const tab = ref('timeline')
let replayMap = null

const cpColumns = [
  { name: 'station', label: '桩号', field: 'station', align: 'left' },
  { name: 'type', label: '类型', field: 'type', align: 'left' },
  { name: 'passed_at', label: '通过时间', field: 'passed_at', align: 'left' },
]

const timelineItems = computed(() => {
  if (!archive.value) return []
  const items = []
  for (const t of (archive.value.timeline || [])) {
    items.push({ icon: t.is_completed ? 'check_circle' : 'radio_button_unchecked', color: t.is_completed ? 'green' : 'grey', title: t.label, time: t.changed_at || '' })
  }
  for (const c of (archive.value.checkpoints || [])) {
    items.push({ icon: 'pin_drop', color: 'blue', title: `${c.station} (${c.type})`, time: c.passed_at || '' })
  }
  for (const a of (archive.value.alerts || [])) {
    items.push({ icon: 'warning', color: { low: 'grey', medium: 'orange', high: 'red', critical: 'deep-orange' }[a.severity] || 'orange', title: `[${a.severity}] ${a.message}`, time: a.timestamp || '' })
  }
  items.sort((a, b) => (a.time || '').localeCompare(b.time || ''))
  return items
})

async function loadOrders() {
  try { const r = await getOrders(0, 500); if (r.code === 200) orders.value = (r.data?.orders || []).filter(o => o.status === 'COMPLETED') } catch (e) { /* */ }
}

async function loadArchive(orderId) {
  selectedId.value = orderId
  try { const r = await getArchive(orderId); if (r.code === 200) { archive.value = r.data; await nextTick(); if (tab.value === 'replay') initReplayMap() } } catch (e) { /* */ }
}

function initReplayMap() {
  if (replayMap) replayMap.destroy()
  const gps = archive.value?.gps_track || []
  const center = gps.length > 0 ? [parseFloat(gps[0].longitude), parseFloat(gps[0].latitude)] : [118.3, 25.5]
  const load = () => {
    replayMap = new window.AMap.Map('replay-map', { center, zoom: 10 })
    if (gps.length > 1) {
      const path = gps.map(p => [parseFloat(p.longitude), parseFloat(p.latitude)])
      const poly = new window.AMap.Polyline({ path, strokeColor: '#2563eb', strokeWeight: 4 }); poly.setMap(replayMap)
      replayMap.setFitView()
    }
    for (const c of (archive.value?.checkpoints || [])) {
      if (c.longitude && c.latitude) new window.AMap.Marker({ position: [parseFloat(c.longitude), parseFloat(c.latitude)], title: c.station }).setMap(replayMap)
    }
  }
  if (window.AMap) load(); else {
    const KEY = import.meta.env.VITE_AMAP_KEY || '0625539f7941518573845dd16fe22316'; const s = document.createElement('script'); s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`; s.onload = load; document.head.appendChild(s)
  }
}

watch(tab, (val) => { if (val === 'replay') nextTick(() => initReplayMap()) })

function exportIt(format) { if (selectedId.value) window.open(getExportUrl(selectedId.value, format), '_blank') }
function fmtDate(d) { if (!d) return ''; return new Date(d).toLocaleDateString('zh-CN') }

onMounted(() => loadOrders())
onBeforeUnmount(() => { if (replayMap) replayMap.destroy() })

defineExpose({ loadArchive })
</script>

<style scoped>
.da-root { width: 100%; height: 100%; }
.da-sidebar { width: 280px; height: 100%; border-right: 1px solid #e2e8f0; background: #fff; }
#replay-map { width: 100%; height: 100%; }
</style>
