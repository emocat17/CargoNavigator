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

      <!-- Vehicle Selection -->
      <div class="q-my-sm">
          <div class="text-subtitle1 q-mb-xs">车辆配置</div>
          <q-card flat bordered class="bg-grey-1">
              <q-card-section class="row items-center q-pa-sm">
                  <div v-if="selectedVehicle" class="col">
                      <div class="text-subtitle2">{{ selectedVehicle.name }}</div>
                      <div class="text-caption text-grey-8">
                          {{ selectedVehicle.length }}x{{ selectedVehicle.width }}x{{ selectedVehicle.height }}m | {{ selectedVehicle.total_weight }}吨 | {{ selectedVehicle.axis_count }}轴
                      </div>
                  </div>
                  <div v-else class="col text-grey-7">
                      请选择运输车辆以获取精准路线
                  </div>
                  <div class="col-auto">
                      <q-btn flat round color="primary" icon="edit_note" @click="showVehicleManager = true">
                          <q-tooltip>管理车辆档案</q-tooltip>
                      </q-btn>
                  </div>
              </q-card-section>
          </q-card>
      </div>

      <!-- Qualification Info Entry -->
      <div class="q-my-sm">
          <div class="text-subtitle1 q-mb-xs">通行资质预审信息</div>
          <q-card flat bordered class="bg-blue-1">
              <q-card-section class="row items-center q-pa-sm">
                  <div class="col text-grey-9">
                      <div class="text-subtitle2">大件运输申请信息录入</div>
                      <div class="text-caption">
                          完善业户、货物及运输计划信息，用于资质预审
                      </div>
                  </div>
                  <div class="col-auto">
                      <q-btn flat round color="primary" icon="assignment" @click="showQualificationManager = true">
                          <q-tooltip>录入申请信息</q-tooltip>
                      </q-btn>
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
    
    <VehicleProfileManager v-model="showVehicleManager" @select="onVehicleSelect" />
    <QualificationManager v-model="showQualificationManager" :sync-source="{ vehicle: selectedVehicle, route: form }" />
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import VehicleProfileManager from './VehicleProfileManager.vue'
import QualificationManager from './QualificationManager.vue'

const props = defineProps({
  loading: Boolean,
  selectingStart: Boolean,
  selectingEnd: Boolean,
  routeResult: Object
})

const emit = defineEmits(['plan-route', 'toggle-select-start', 'toggle-select-end'])

const showVehicleManager = ref(false)
const showQualificationManager = ref(false)
const selectedVehicle = ref(null)

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

const onVehicleSelect = (vehicle) => {
    selectedVehicle.value = vehicle
}

const onSubmit = () => {
  const payload = { ...form }
  if (selectedVehicle.value) {
      payload.vehicle = {
          length: selectedVehicle.value.length,
          width: selectedVehicle.value.width,
          height: selectedVehicle.value.height,
          weight: selectedVehicle.value.total_weight,
          axis_weight: 10, // Default or calculate from axis_weights? Using simple placeholder for now or derive max.
          // Note: Backend VehicleInfo expects specific fields. 
          // axis_weight in Amap API is usually "heaviest axle load".
          // We can calculate max(axis_weights) here.
          axis_weight: Math.max(...(selectedVehicle.value.axis_weights || [0]))
      }
  }
  emit('plan-route', payload)
}

const setAddress = (type, val) => {
    if (type === 'start') form.origin = val
    if (type === 'end') form.destination = val
}

defineExpose({ setAddress })
</script>
