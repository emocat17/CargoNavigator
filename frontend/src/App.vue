<template>
  <q-layout view="hHh lpR fFf" class="app-root">
    <!-- ===== 顶部导航栏 ===== -->
    <q-header elevated class="nav-header">
      <q-toolbar>
        <q-toolbar-title class="text-weight-bold">
          <q-icon name="local_shipping" class="q-mr-sm" />
          CargoNavigator
        </q-toolbar-title>
        <q-tabs :model-value="route.name" @update:model-value="onTabChange" dense shrink indicator-color="white" active-color="white" class="text-grey-5">
          <q-tab name="planner" icon="explore" label="路线规划" />
          <q-tab name="transport" icon="local_shipping" label="运输管理" />
          <q-tab name="archive" icon="archive" label="数字档案" />
        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>

    <!-- ===== AI 浮球（全局） ===== -->
    <AiAssistant
      :routes="sharedStore.routes"
      :selected-route-index="sharedStore.selectedIdx"
      :vehicle="sharedStore.vehicle"
      @plan-route="handlePlanRoute"
    />
  </q-layout>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import AiAssistant from './components/AiAssistant.vue'
import { sharedStore } from './store/index.js'

const router = useRouter()
const route = useRoute()

function onTabChange(tabName) {
  router.push({ name: tabName })
}

function handlePlanRoute(payload) {
  // 路线规划结果回调（由 AiAssistant 触发）
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
body {
  margin: 0;
  background: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
</style>
