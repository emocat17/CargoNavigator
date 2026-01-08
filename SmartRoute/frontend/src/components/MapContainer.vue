<template>
  <div id="map-container" class="map-container"></div>
</template>

<script setup>
import { onMounted, onUnmounted, shallowRef } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

// Props definition
const props = defineProps({
  apiKey: {
    type: String,
    default: 'YOUR_AMAP_JS_API_KEY' // 替换为您的 JS API Key
  },
  securityCode: {
    type: String,
    default: 'YOUR_AMAP_SECURITY_CODE' // 替换为您的安全密钥
  }
})

// Map instance
const map = shallowRef(null)
const AMapObj = shallowRef(null) // AMap object reference

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map.value) {
    map.value.destroy()
  }
})

const initMap = () => {
  // 设置安全密钥
  window._AMapSecurityConfig = {
    securityJsCode: props.securityCode,
  }

  AMapLoader.load({
    key: props.apiKey,
    version: "2.0",
    plugins: ['AMap.Driving', 'AMap.TruckDriving', 'AMap.Polyline', 'AMap.Marker'],
  })
    .then((AMap) => {
      AMapObj.value = AMap
      map.value = new AMap.Map("map-container", {
        viewMode: "3D",
        zoom: 11,
        center: [116.397428, 39.90923], // Default Beijing
      })
      console.log("Map initialized successfully")
    })
    .catch((e) => {
      console.error("Map initialization failed:", e)
    })
}

// Expose methods for parent component
const setCenter = (lng, lat) => {
  if (map.value) {
    map.value.setCenter([lng, lat])
  }
}

const drawPath = (pathPoints) => {
  if (!map.value || !AMapObj.value) return

  // Clear existing overlays
  map.value.clearMap()

  // pathPoints format: "lon,lat;lon,lat;..."
  const pathArr = pathPoints.split(';').map(pt => {
    const [lng, lat] = pt.split(',')
    return [parseFloat(lng), parseFloat(lat)]
  })

  // Draw Polyline
  const polyline = new AMapObj.value.Polyline({
    path: pathArr,
    isOutline: true,
    outlineColor: '#ffeeff',
    borderWeight: 3,
    strokeColor: "#3366FF", 
    strokeOpacity: 1,
    strokeWeight: 6,
    strokeStyle: "solid",
    strokeDasharray: [10, 5],
    lineJoin: 'round',
    lineCap: 'round',
    zIndex: 50,
  })

  map.value.add(polyline)
  map.value.setFitView([polyline])
  
  // Add Start/End Markers
  const startMarker = new AMapObj.value.Marker({
    position: pathArr[0],
    title: 'Start',
    label: { content: '起', offset: new AMapObj.value.Pixel(0, 0) }
  })
  
  const endMarker = new AMapObj.value.Marker({
    position: pathArr[pathArr.length - 1],
    title: 'End',
    label: { content: '终', offset: new AMapObj.value.Pixel(0, 0) }
  })
  
  map.value.add([startMarker, endMarker])
}

defineExpose({
  setCenter,
  drawPath
})
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: relative;
}
</style>
