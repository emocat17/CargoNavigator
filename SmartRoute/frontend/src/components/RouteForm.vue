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

      <div class="row justify-end">
        <q-btn 
            label="开始规划" 
            type="submit" 
            color="primary" 
            :loading="loading" 
            class="full-width text-subtitle1"
            size="lg"
            icon="directions"
        />
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
  routeResult: Object
})

const emit = defineEmits(['plan-route', 'toggle-select-start', 'toggle-select-end'])

// const showVehicleManager = ref(false)
const showQualificationManager = ref(false)
// const selectedVehicle = ref(null)

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

// const onVehicleSelect = (vehicle) => {
//    selectedVehicle.value = vehicle
// }

const onSubmit = () => {
  const payload = { ...form }
  
  if (hasValidVehicleData.value) {
      // Parse dimensions from string "L,W,H"
      const dims = applicationData.total_size_arr_str.split(',').map(Number)
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
          load_weights: applicationData.axis_weights_str ? applicationData.axis_weights_str.split(',').map(Number) : [],
          axis_distances: applicationData.axis_distances_str ? applicationData.axis_distances_str.split(',').map(Number) : []
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
}

defineExpose({ setAddress })
</script>
