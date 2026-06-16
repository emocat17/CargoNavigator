<template>
  <q-layout view="hHh lpR fFf" class="app-root">
    <!-- ===== 顶部导航栏 ===== -->
    <q-header elevated class="nav-header">
      <q-toolbar>
        <q-toolbar-title class="text-weight-bold">
          <q-icon name="local_shipping" class="q-mr-sm" />
          CargoNavigator
        </q-toolbar-title>
        <q-tabs v-model="currentPage" dense shrink indicator-color="white" active-color="white" class="text-grey-5">
          <q-tab name="planner" icon="explore" label="路线规划" />
          <q-tab name="transport" icon="local_shipping" label="运输管理" />
          <q-tab name="archive" icon="archive" label="数字档案" />
        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <!-- ===== 页面1: 路线规划 ===== -->
      <q-page v-show="currentPage === 'planner'" class="page-full">
        <RoutePlanner
          ref="routePlannerRef"
          :routes="routes"
          :selected-route-index="selectedRouteIndex"
          @plan-route="handlePlanRoute"
          @select-route="selectedRouteIndex = $event"
          @view-transport="currentPage = 'transport'"
        />
      </q-page>

      <!-- ===== 页面2: 运输管理 ===== -->
      <q-page v-if="currentPage === 'transport'" class="page-full">
        <TransportManager
          ref="transportManagerRef"
          @view-archive="handleViewArchive"
        />
      </q-page>

      <!-- ===== 页面3: 数字档案 ===== -->
      <q-page v-if="currentPage === 'archive'" class="page-full">
        <DigitalArchive ref="digitalArchiveRef" />
      </q-page>
    </q-page-container>

    <!-- ===== AI 浮球（全局） ===== -->
    <AiAssistant
      :routes="routes"
      :selected-route-index="selectedRouteIndex"
      :vehicle="currentVehicle"
      @plan-route="handlePlanRoute"
    />
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import RoutePlanner from './components/RoutePlanner.vue'
import TransportManager from './components/TransportManager.vue'
import DigitalArchive from './components/DigitalArchive.vue'
import AiAssistant from './components/AiAssistant.vue'

const currentPage = ref('planner')
const routes = ref([])
const selectedRouteIndex = ref(0)
const currentVehicle = ref(null)
const routePlannerRef = ref(null)
const transportManagerRef = ref(null)
const digitalArchiveRef = ref(null)

// 路线规划结果回调
function handlePlanRoute(payload) {
  console.log('[App] Plan route:', payload)
}

// 从运输管理跳转到档案
function handleViewArchive(orderId) {
  digitalArchiveRef.value?.loadArchive(orderId)
  currentPage.value = 'archive'
}
</script>

<style>
.app-root {
  background: #0f172a;
}
.nav-header {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}
.page-full {
  height: calc(100vh - 50px);
  overflow: hidden;
}
body {
  margin: 0;
  background: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
</style>
