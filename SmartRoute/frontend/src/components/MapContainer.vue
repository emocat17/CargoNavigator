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
    if (!map.value || !AMapObj.value) {
        console.warn("Map or AMap object not initialized yet.")
        return
    }
    if (!pathPoints) {
        console.warn("No path points provided to drawRoutePolyline.")
        return
    }

    console.log("Drawing route with points length:", pathPoints.length)

    if (routePolyline.value) {
        map.value.remove(routePolyline.value)
        routePolyline.value = null
    }

    try {
        // pathPoints format: "lon,lat;lon,lat;..."
        const rawPoints = pathPoints.split(';')
        const pathArr = []
        
        for (const pt of rawPoints) {
            if (!pt || pt.trim() === '') continue
            
            const parts = pt.split(',')
            if (parts.length < 2) continue
            
            const lng = parseFloat(parts[0])
            const lat = parseFloat(parts[1])
            
            if (!isNaN(lng) && !isNaN(lat)) {
                pathArr.push([lng, lat])
            }
        }

        console.log(`Parsed ${pathArr.length} valid points for polyline.`)

        if (pathArr.length === 0) {
             console.warn("No valid points found after parsing.")
             return
        }

        // Draw Polyline
        routePolyline.value = new AMapObj.value.Polyline({
            path: pathArr,
            isOutline: true, // Add outline for better contrast
            outlineColor: 'white',
            borderWeight: 2,
            strokeColor: "#1890FF", 
            strokeOpacity: 1.0,
            strokeWeight: 8, // Thicker
            strokeStyle: "solid",
            lineJoin: 'round',
            lineCap: 'round',
            zIndex: 1000, // Max zIndex
            showDir: true,
        })

        map.value.add(routePolyline.value)
        
        // Fit view to include route with padding
        map.value.setFitView([routePolyline.value], false, [50, 50, 50, 50])
        
        // If strict requirement for start point:
        // setTimeout(() => {
        //    map.value.setZoomAndCenter(14, pathArr[0])
        // }, 1000)
        // I will stick to setFitView because "no path displayed" is the complaint. 
        // Showing the whole path is the best proof it works.
        
    } catch (e) {
        console.error("Error drawing polyline:", e)
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
