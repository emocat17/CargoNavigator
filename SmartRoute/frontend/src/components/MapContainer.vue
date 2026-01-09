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
    default: 'YOUR_AMAP_JS_API_KEY'
  },
  securityCode: {
    type: String,
    default: 'YOUR_AMAP_SECURITY_CODE'
  }
})

// Map instance
const map = shallowRef(null)
const AMapObj = shallowRef(null) // AMap object reference
const routePolylines = shallowRef([]) // Store multiple polylines for traffic segments

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map.value) {
    map.value.destroy()
  }
})

const initMap = () => {
  // 设置安全密钥 (必须在 Loader 加载前设置)
  if (props.securityCode) {
      window._AMapSecurityConfig = {
        securityJsCode: props.securityCode,
      }
  }

  AMapLoader.load({
    key: props.apiKey,
    version: "2.0",
    plugins: [], 
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
const waypointMarkers = new Map()

const updateMarker = (type, lng, lat, index = -1) => {
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
  } else if (type === 'waypoint' && index > -1) {
    if (waypointMarkers.has(index)) {
        waypointMarkers.get(index).setPosition(position)
    } else {
        const marker = new AMapObj.value.Marker({
            position: position,
            title: `途经点 ${index + 1}`,
            label: { content: `${index + 1}`, direction: 'top' }
        })
        map.value.add(marker)
        waypointMarkers.set(index, marker)
    }
  }
  
  // Fit view to include all markers
  const markersToFit = []
  if (startMarker.value) markersToFit.push(startMarker.value)
  if (endMarker.value) markersToFit.push(endMarker.value)
  waypointMarkers.forEach(m => markersToFit.push(m))
  
  if (markersToFit.length > 0) {
    map.value.setFitView(markersToFit)
  } else {
     map.value.setCenter(position)
  }
}

const removeMarker = (type, index) => {
    if (type === 'waypoint') {
        if (waypointMarkers.has(index)) {
            const marker = waypointMarkers.get(index)
            if (map.value) map.value.remove(marker)
            waypointMarkers.delete(index)
        }
        
        // Re-index subsequent markers
        const newMap = new Map()
        // Convert to array to sort keys to process safely? Map iteration order is insertion order usually, but safer to just iterate and build new map
        // Actually, we need to iterate all current markers and shift those > index
        
        // We need to be careful not to overwrite.
        // Create a temporary list of entries to update
        const updates = []
        waypointMarkers.forEach((marker, key) => {
            if (key > index) {
                updates.push({ oldKey: key, marker: marker })
            }
        })
        
        // Apply updates
        updates.sort((a, b) => a.oldKey - b.oldKey).forEach(({ oldKey, marker }) => {
            waypointMarkers.delete(oldKey)
            const newKey = oldKey - 1
            marker.setLabel({ content: `${newKey + 1}`, direction: 'top' })
            marker.setTitle(`途经点 ${newKey + 1}`)
            waypointMarkers.set(newKey, marker)
        })
    }
}

// Expose methods for parent component
const setCenter = (lng, lat) => {
  if (map.value) {
    map.value.setCenter([lng, lat])
  }
}

const drawPath = (pathPoints, steps) => {
  if (!map.value || !AMapObj.value) {
    console.warn("Map or AMap object not initialized yet.")
    return
  }
  
  // Clear existing polylines
  if (routePolylines.value.length > 0) {
    map.value.remove(routePolylines.value)
    routePolylines.value = []
  }

  const polylinesToDraw = []

  // Helper to parse coordinate string
  const parsePath = (pathStr) => {
    if (!pathStr) return []
    const pathArr = []
    const rawPoints = pathStr.split(';')
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
    return pathArr
  }

  // Color map
  const statusColors = {
    "畅通": "#00B578", // Green
    "缓行": "#FFAA00", // Yellow
    "拥堵": "#FF4D4F", // Red
    "严重拥堵": "#990000", // Dark Red
    "未知": "#1890FF"  // Blue
  }

  let hasTrafficData = false

  if (steps && steps.length > 0) {
    // Check if we actually have TMC data
    const hasTmc = steps.some(step => step.tmcs && step.tmcs.length > 0)
    
    if (hasTmc) {
      hasTrafficData = true
      // console.log("Drawing route with traffic data...")
      
      let currentPath = []
      let currentStatus = null

      const flushPath = () => {
          if (currentPath.length > 0 && currentStatus) {
            const color = statusColors[currentStatus] || statusColors["未知"]
            const polyline = new AMapObj.value.Polyline({
              path: currentPath,
              isOutline: true,
              outlineColor: 'white',
              borderWeight: 1,
              strokeColor: color,
              strokeOpacity: 1.0,
              strokeWeight: 8,
              strokeStyle: "solid",
              lineJoin: 'round',
              lineCap: 'round',
              zIndex: 1000,
              showDir: true,
            })
            polylinesToDraw.push(polyline)
          }
      }

      for (const step of steps) {
        if (step.tmcs && step.tmcs.length > 0) {
          for (const tmc of step.tmcs) {
            const pathArr = parsePath(tmc.polyline)
            if (pathArr.length === 0) continue

            // If status changes, flush and start new
            if (tmc.status !== currentStatus) {
                flushPath()
                currentStatus = tmc.status
                currentPath = pathArr
            } else {
                 // Same status, append points
                 // Optimization: Use push spread to avoid O(N^2) array copying
                 currentPath.push(...pathArr)
             }
           }
         } else {
             // Step without TMCs - treat as "未知" or just break continuity?
             // Usually we treat it as a segment.
             const pathArr = parsePath(step.polyline)
             if (pathArr.length > 0) {
                 if (currentStatus !== "未知") {
                     flushPath()
                     currentStatus = "未知"
                     currentPath = pathArr
                 } else {
                     currentPath.push(...pathArr)
                 }
             }
         }
      }
      // Flush remaining
      flushPath()

    }
  }

  if (!hasTrafficData) {
    console.log("Drawing route without traffic data (fallback)...")
    // Fallback to full path
    const pathArr = parsePath(pathPoints)
    if (pathArr.length > 0) {
      const polyline = new AMapObj.value.Polyline({
        path: pathArr,
        isOutline: true,
        outlineColor: 'white',
        borderWeight: 2,
        strokeColor: "#1890FF",
        strokeOpacity: 1.0,
        strokeWeight: 8,
        strokeStyle: "solid",
        lineJoin: 'round',
        lineCap: 'round',
        zIndex: 1000,
        showDir: true,
      })
      polylinesToDraw.push(polyline)
    }
  }

  if (polylinesToDraw.length > 0) {
    map.value.add(polylinesToDraw)
    routePolylines.value = polylinesToDraw
    map.value.setFitView(polylinesToDraw, false, [50, 50, 50, 50])
  }
}

defineExpose({
  setCenter,
  drawPath,
  updateMarker,
  removeMarker
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
