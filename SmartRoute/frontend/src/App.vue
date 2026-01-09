<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn dense flat round icon="menu" @click="toggleDrawer" />
        <q-toolbar-title>
          SmartRoute (大型货车智能选线)
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-drawer show-if-above v-model="drawerOpen" side="left" bordered :width="420" class="bg-grey-1">
      <q-tabs
        v-model="tab"
        dense
        class="text-grey"
        active-color="primary"
        indicator-color="primary"
        align="justify"
        narrow-indicator
      >
        <q-tab name="planning" icon="directions" label="路径规划" />
        <q-tab name="chat" icon="smart_toy" label="智能问答" />
      </q-tabs>

      <q-separator />

      <q-tab-panels v-model="tab" animated>
        <q-tab-panel name="planning" class="q-pa-none">
           <RouteForm 
            ref="routeFormRef"
            :loading="loading"
            :selecting-start="selectingStart"
            :selecting-end="selectingEnd"
            @plan-route="handlePlanRoute"
            @toggle-select-start="toggleSelectStart"
            @toggle-select-end="toggleSelectEnd"
          />
        </q-tab-panel>

        <q-tab-panel name="chat">
           <SmartQA />
        </q-tab-panel>
      </q-tab-panels>
    </q-drawer>

    <!-- Right Drawer for Route Result -->
    <q-drawer 
        v-model="rightDrawerOpen" 
        side="right" 
        bordered 
        overlay
        :width="500" 
        class="bg-white shadow-3"
    >
        <RouteResultPanel 
            v-if="routes && routes.length > 0" 
            :routes="routes"
            :vehicle="currentVehicle"
            :selected-index="selectedRouteIndex" 
            @close="rightDrawerOpen = false"
            @select-route="handleSelectRoute"
        />
    </q-drawer>

    <q-page-container>
      <div class="row relative-position" style="height: calc(100vh - 50px);">
        <!-- Map Component (Always visible but z-index handled if needed, currently side-by-side) -->
        <div class="col-12 full-height">
          <MapContainer 
            ref="mapRef"
            :apiKey="amapKey"
            :securityCode="amapSecurityCode"
            @map-click="handleMapClick"
          />
        </div>
      </div>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import MapContainer from './components/MapContainer.vue'
import RouteForm from './components/RouteForm.vue'
import RouteResultPanel from './components/RouteResultPanel.vue'
import SmartQA from './components/SmartQA.vue'
import axios from 'axios'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const mapRef = ref(null)
const routeFormRef = ref(null)
const loading = ref(false)
const drawerOpen = ref(true)
const rightDrawerOpen = ref(false)
const tab = ref('planning')

const amapKey = import.meta.env.VITE_AMAP_KEY
const amapSecurityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

const selectingStart = ref(false)
const selectingEnd = ref(false)
const routes = ref([])
const selectedRouteIndex = ref(0)
const currentVehicle = ref(null)

const toggleDrawer = () => {
  drawerOpen.value = !drawerOpen.value
}

const toggleSelectStart = () => {
    selectingStart.value = !selectingStart.value
    selectingEnd.value = false // Mutually exclusive
    if (selectingStart.value) {
        $q.notify({ type: 'info', message: '请在地图上点击选择起点', position: 'top' })
    }
}

const toggleSelectEnd = () => {
    selectingEnd.value = !selectingEnd.value
    selectingStart.value = false // Mutually exclusive
    if (selectingEnd.value) {
        $q.notify({ type: 'info', message: '请在地图上点击选择终点', position: 'top' })
    }
}

const handleMapClick = (e) => {
    // Only handle clicks if on planning tab and selecting
    if (tab.value !== 'planning') return

    const { lng, lat } = e
    const coordStr = `${lng.toFixed(6)},${lat.toFixed(6)}`
    
    if (selectingStart.value) {
        if (routeFormRef.value) routeFormRef.value.setAddress('start', coordStr)
        if (mapRef.value) mapRef.value.updateMarker('start', lng, lat)
        selectingStart.value = false
        $q.notify({ type: 'positive', message: '起点已选择', position: 'top', timeout: 1000 })
    } else if (selectingEnd.value) {
        if (routeFormRef.value) routeFormRef.value.setAddress('end', coordStr)
        if (mapRef.value) mapRef.value.updateMarker('end', lng, lat)
        selectingEnd.value = false
        $q.notify({ type: 'positive', message: '终点已选择', position: 'top', timeout: 1000 })
    }
}

const handlePlanRoute = async (formData) => {
  loading.value = true
  
  // Update current vehicle info
  currentVehicle.value = formData.vehicle || {
    length: 13.5,
    width: 2.55,
    height: 4.0,
    weight: 49.0,
    axis_weight: 10.0
  }

  try {
    const response = await axios.post('http://localhost:9876/api/v1/routes/plan', {
      origin: formData.origin,
      destination: formData.destination,
      // strategy: formData.strategy, // Backend ignores strategy now
      vehicle: currentVehicle.value
    })

    if (response.data.code === 200) {
      const newRoutes = response.data.data.routes
      if (newRoutes && newRoutes.length > 0) {
        routes.value = newRoutes
        selectedRouteIndex.value = 0
        rightDrawerOpen.value = true // Open right drawer
        
        $q.notify({
          type: 'positive',
          message: `规划成功！共找到 ${newRoutes.length} 条路线`
        })
        
        // Draw first route on map
        const route = newRoutes[0]
        if (mapRef.value) {
          mapRef.value.drawPath(route.path_points, route.steps)
          
          // Also update markers positions based on the result path
          const pathArr = route.path_points.split(';')
          if (pathArr.length > 0) {
             const startPt = pathArr[0].split(',')
             const endPt = pathArr[pathArr.length-1].split(',')
             mapRef.value.updateMarker('start', parseFloat(startPt[0]), parseFloat(startPt[1]))
             mapRef.value.updateMarker('end', parseFloat(endPt[0]), parseFloat(endPt[1]))
          }
        }
      }
    } else {
      $q.notify({
        type: 'negative',
        message: '规划失败: ' + response.data.msg
      })
    }
  } catch (error) {
    console.error(error)
    $q.notify({
      type: 'negative',
      message: '请求出错，请检查网络或后端服务'
    })
  } finally {
    loading.value = false
  }
}

const handleSelectRoute = (index) => {
    selectedRouteIndex.value = index
    const route = routes.value[index]
    if (mapRef.value && route) {
        mapRef.value.drawPath(route.path_points, route.steps)
    }
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  overflow: hidden;
}
</style>
