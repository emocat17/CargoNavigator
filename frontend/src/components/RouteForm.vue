<template>
  <div class="q-pa-md">
    <div class="text-h6 q-mb-md">路径规划</div>
    
    <q-form @submit="onSubmit" class="q-gutter-md">
      <!-- Origin Input -->
      <div class="row items-start q-col-gutter-sm">
         <div class="col">
            <q-input
                filled
                v-model="form.origin"
                label="起点"
                hint="输入地址或点击地图图标选点"
                :rules="[val => !!val || '请输入起点']"
                input-style="font-size: 1.25rem"
                label-style="font-size: 1.1rem"
            >
                <template v-slot:append>
                    <q-icon 
                        name="place" 
                        class="cursor-pointer" 
                        size="md"
                        :color="selectingStart ? 'primary' : ''"
                        @click="$emit('toggle-select-start')"
                    >
                        <q-tooltip>在地图上选点</q-tooltip>
                    </q-icon>
                </template>
            </q-input>
         </div>
      </div>
      
      <!-- Destination Input -->
      <div class="row items-start q-col-gutter-sm">
         <div class="col">
            <q-input
                filled
                v-model="form.destination"
                label="终点"
                hint="输入地址或点击地图图标选点"
                :rules="[val => !!val || '请输入终点']"
                input-style="font-size: 1.25rem"
                label-style="font-size: 1.1rem"
            >
                <template v-slot:append>
                    <q-icon 
                        name="place" 
                        class="cursor-pointer" 
                        size="md"
                        :color="selectingEnd ? 'primary' : ''"
                        @click="$emit('toggle-select-end')"
                    >
                        <q-tooltip>在地图上选点</q-tooltip>
                    </q-icon>
                </template>
            </q-input>
         </div>
      </div>

      <!-- Waypoints Input -->
      <div v-if="waypoints.length > 0" class="q-mb-sm">
        <div class="text-subtitle2 q-mb-xs text-grey-8">途经点</div>
        <div v-for="(wp, index) in waypoints" :key="index" class="row items-center q-mb-sm q-col-gutter-sm">
            <div class="col">
                <q-input
                    filled
                    dense
                    v-model="waypoints[index]"
                    :label="`途经点 ${index + 1}`"
                    placeholder="输入地址或经纬度"
                >
                     <template v-slot:prepend>
                        <q-icon name="add_location_alt" size="sm" />
                    </template>
                    <template v-slot:append>
                        <q-icon 
                            name="place" 
                            class="cursor-pointer" 
                            size="md"
                            :color="selectingWaypointIndex === index ? 'primary' : ''"
                            @click="$emit('toggle-select-waypoint', index)"
                        >
                            <q-tooltip>在地图上选点</q-tooltip>
                        </q-icon>
                    </template>
                </q-input>
            </div>
            <div class="col-auto">
                <q-btn flat round dense color="negative" icon="remove_circle_outline" @click="removeWaypoint(index)">
                    <q-tooltip>移除此途经点</q-tooltip>
                </q-btn>
            </div>
        </div>
      </div>
      
      <!-- Add Waypoint Button -->
      <div class="row q-mb-md" v-if="enableWaypoints">
          <q-btn flat dense color="primary" icon="add" label="添加途经点" @click="addWaypoint" size="sm" />
      </div>

      <!-- Departure Time Input -->
      <div class="row items-start q-col-gutter-sm">
         <div class="col">
            <q-input 
                filled 
                v-model="form.departure_time" 
                label="预计出发时间 (选填)" 
                hint="若为空则默认当前时间出发" 
                clearable
            >
                <template v-slot:prepend>
                    <q-icon name="event" class="cursor-pointer">
                        <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                            <div class="row no-wrap">
                                <q-date v-model="form.departure_time" mask="YYYY-MM-DD HH:mm" />
                                <q-separator vertical />
                                <q-time v-model="form.departure_time" mask="YYYY-MM-DD HH:mm" format24h />
                            </div>
                            <div class="row items-center justify-end q-pa-sm bg-white">
                                <q-btn v-close-popup label="确定" color="primary" flat />
                            </div>
                        </q-popup-proxy>
                    </q-icon>
                </template>
            </q-input>
         </div>
      </div>

      <!-- Task & Vehicle Configuration (Unified) -->
      <div class="q-my-sm">
          <div class="text-subtitle1 q-mb-xs">运输任务与车辆配置</div>
          <q-card flat bordered class="bg-blue-1">
              <q-card-section class="q-pa-sm">
                  <div class="row items-center">
                      <div class="col">
                          <div class="text-subtitle2">任务详情配置</div>
                          <div class="text-caption text-grey-9">
                              <span v-if="hasValidVehicleData">
                                  车辆: {{ applicationData.total_size_arr_str }}米 | {{ applicationData.total_weight }}吨 | {{ applicationData.axle_count }}轴
                              </span>
                              <span v-else>
                                  请配置车辆及货物信息以获取精准路线
                              </span>
                          </div>
                      </div>
                      <div class="col-auto">
                          <q-btn flat round color="primary" icon="edit_document" @click="showQualificationManager = true">
                              <q-tooltip>编辑任务详情</q-tooltip>
                          </q-btn>
                      </div>
                  </div>
              </q-card-section>
          </q-card>
      </div>

      <!-- Route Count Selector -->
      <div class="row q-col-gutter-sm q-mt-xs">
        <div class="col-12">
          <div class="text-caption text-grey-8 q-mb-xs">期望路线方案数 ({{ routeCount }})</div>
          <q-slider
            v-model="routeCount"
            :min="1"
            :max="5"
            :step="1"
            label
            label-always
            color="primary"
            markers
          />
        </div>
      </div>

      <!-- Submit Button -->
      <div class="row q-mt-md">
        <q-btn 
            unelevated
            color="primary" 
            label="开始规划" 
            class="full-width" 
            size="lg"
            :loading="loading"
            @click="onSubmit"
        >
            <template v-slot:loading>
                <q-spinner-dots class="on-left" />
                计算中...
            </template>
        </q-btn>
      </div>
    </q-form>
    
    <!-- VehicleProfileManager is removed/hidden as requested -->
    <!-- <VehicleProfileManager v-model="showVehicleManager" @select="onVehicleSelect" /> -->
    
    <QualificationManager 
        v-model="showQualificationManager" 
        :sync-source="{ vehicle: null, route: form }"
        :initial-data="applicationData"
        @save="onApplicationSave"
    />
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import QualificationManager from './QualificationManager.vue'
// import VehicleProfileManager from './VehicleProfileManager.vue'

const props = defineProps({
  loading: Boolean,
  selectingStart: Boolean,
  selectingEnd: Boolean,
  selectingWaypointIndex: {
      type: Number,
      default: -1
  },
  routeResult: Object
})

const emit = defineEmits(['plan-route', 'toggle-select-start', 'toggle-select-end', 'toggle-select-waypoint', 'remove-waypoint'])

const showQualificationManager = ref(false)
const routeCount = ref(3)
const waypoints = ref([])

const applicationData = reactive({
    total_size_arr_str: '', 
    total_weight: null,
    axle_count: null,
    axis_weights_str: '',
    axis_distances_str: ''
    // ... other fields if needed for display
})

const hasValidVehicleData = computed(() => {
    return applicationData.total_size_arr_str && applicationData.total_weight
})

// Load initial data from localStorage to show summary immediately
onMounted(() => {
    const saved = localStorage.getItem('qualification_form_data')
    if (saved) {
        try {
            Object.assign(applicationData, JSON.parse(saved))
        } catch (e) {}
    }
})

const onApplicationSave = (data) => {
    Object.assign(applicationData, data)
}

const form = reactive({
  origin: '福建省三明厦钨新能源',
  destination: '福建省平潭跨境电商园',
  strategy: 0,
  departure_time: null
})

const strategyOptions = [
  { label: '速度优先', value: 0 },
  { label: '费用优先', value: 1 },
  { label: '距离优先', value: 2 }
]

const addWaypoint = () => {
    if (waypoints.value.length >= 16) {
        $q.notify({ type: 'warning', message: '最多支持 16 个途经点' })
        return
    }
    waypoints.value.push('')
}

const removeWaypoint = (index) => {
    waypoints.value.splice(index, 1)
    emit('remove-waypoint', index)
}

// const onVehicleSelect = (vehicle) => {
//    selectedVehicle.value = vehicle
// }

const parseArrayStr = (str) => {
    if (!str) return []
    return str.replace(/，/g, ',').split(',').map(s => s.trim()).filter(s => s !== '')
}

const onSubmit = () => {
  const payload = { 
      ...form, 
      route_count: routeCount.value,
      waypoints: waypoints.value.filter(wp => wp && wp.trim())
  }
  
  if (hasValidVehicleData.value) {
      // Parse dimensions from string "L,W,H"
      const dims = parseArrayStr(applicationData.total_size_arr_str).map(Number)
      const length = dims[0] || 0
      const width = dims[1] || 0
      const height = dims[2] || 0
      
      payload.vehicle = {
          length: length,
          width: width,
          height: height,
          weight: applicationData.total_weight,
          axis_count: applicationData.axle_count || 0,
          // Default axis weight if not available
          axis_weight: 10,
          load_weights: applicationData.axis_weights_str ? parseArrayStr(applicationData.axis_weights_str).map(Number) : [],
          axis_distances: applicationData.axis_distances_str ? parseArrayStr(applicationData.axis_distances_str).map(Number) : []
      }
  } else {
      // Fallback or Alert?
      // For now, let backend handle missing vehicle or use defaults if allowed
  }
  
  emit('plan-route', payload)
}

const setAddress = (type, val) => {
    if (type === 'start') form.origin = val
    if (type === 'end') form.destination = val
    if (type.startsWith('waypoint-')) {
        const idx = parseInt(type.split('-')[1])
        if (!isNaN(idx) && idx >= 0 && idx < waypoints.value.length) {
            waypoints.value[idx] = val
        }
    }
}

defineExpose({ setAddress })
</script>
