<template>
  <div id="map-container" class="map-container"></div>
</template>

<script setup>
import { onMounted, onUnmounted, shallowRef } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

const emit = defineEmits(['map-click'])

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
    plugins: ['AMap.Driving', 'AMap.TruckDriving', 'AMap.Polyline', 'AMap.Marker', 'AMap.Pixel'],
  })
    .then((AMap) => {
      AMapObj.value = AMap
      map.value = new AMap.Map("map-container", {
        viewMode: "3D",
        zoom: 11,
        center: [116.397428, 39.90923], // Default Beijing
      })
      
      // Click listener
      map.value.on('click', (e) => {
        emit('map-click', { lng: e.lnglat.getLng(), lat: e.lnglat.getLat() })
      })

      console.log("Map initialized successfully")
    })
    .catch((e) => {
      console.error("Map initialization failed:", e)
    })
}

// Markers
const startMarker = shallowRef(null)
const endMarker = shallowRef(null)

const updateMarker = (type, lng, lat) => {
  if (!map.value || !AMapObj.value) return
  
  const position = [lng, lat]
  
  if (type === 'start') {
    if (startMarker.value) {
      startMarker.value.setPosition(position)
    } else {
      startMarker.value = new AMapObj.value.Marker({
        position: position,
        title: '起点',
        label: { content: '起', direction: 'top' }
      })
      map.value.add(startMarker.value)
    }
  } else if (type === 'end') {
    if (endMarker.value) {
      endMarker.value.setPosition(position)
    } else {
      endMarker.value = new AMapObj.value.Marker({
        position: position,
        title: '终点',
        label: { content: '终', direction: 'top' }
      })
      map.value.add(endMarker.value)
    }
  }
  
  // Fit view to include markers if both exist
  if (startMarker.value && endMarker.value) {
    map.value.setFitView([startMarker.value, endMarker.value])
  } else {
     map.value.setCenter(position)
  }
}

// Expose methods for parent component
const setCenter = (lng, lat) => {
  if (map.value) {
    map.value.setCenter([lng, lat])
  }
}

const routePolyline = shallowRef(null)

const drawRoutePolyline = (pathPoints) => {
    if (!map.value || !AMapObj.value) return

    if (routePolyline.value) {
        map.value.remove(routePolyline.value)
    }

    // pathPoints format: "lon,lat;lon,lat;..."
    const pathArr = pathPoints.split(';').map(pt => {
        const [lng, lat] = pt.split(',')
        return [parseFloat(lng), parseFloat(lat)]
    })

    // Draw Polyline
    routePolyline.value = new AMapObj.value.Polyline({
        path: pathArr,
        isOutline: false, // User requested specific style, remove outline to be clean or keep if needed. Let's follow "High light color #1890FF"
        borderWeight: 0,
        strokeColor: "#1890FF", 
        strokeOpacity: 0.8,
        strokeWeight: 4,
        strokeStyle: "solid",
        lineJoin: 'round',
        lineCap: 'round',
        zIndex: 50,
    })

    map.value.add(routePolyline.value)
    
    // Fit view to include route and markers, set zoom to 14 if possible but setFitView overrides zoom. 
    // User asked: "自动将地图视角定位到路径起点，缩放级别设置为14"
    // So we should center on start point and zoom 14. 
    // BUT usually seeing the whole route is better. 
    // Let's follow the user instruction strictly: "Automatic positioning to route start point, zoom level 14".
    
    if (pathArr.length > 0) {
        map.value.setZoomAndCenter(14, pathArr[0])
    } else {
        const overlays = [routePolyline.value]
        if (startMarker.value) overlays.push(startMarker.value)
        if (endMarker.value) overlays.push(endMarker.value)
        map.value.setFitView(overlays)
    }
}

defineExpose({
  setCenter,
  drawPath: drawRoutePolyline,
  updateMarker
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
