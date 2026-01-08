<template>
  <div class="q-pa-md">
    <div class="text-h6 q-mb-md">路径规划</div>
    
    <q-form @submit="onSubmit" class="q-gutter-md">
      <!-- Origin Input -->
      <div class="row items-start q-col-gutter-sm">
         <div class="col">
            <q-input
                filled
                dense
                v-model="form.origin"
                label="起点"
                hint="输入地址或点击地图图标选点"
                :rules="[val => !!val || '请输入起点']"
            >
                <template v-slot:append>
                    <q-icon 
                        name="place" 
                        class="cursor-pointer" 
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
                dense
                v-model="form.destination"
                label="终点"
                hint="输入地址或点击地图图标选点"
                :rules="[val => !!val || '请输入终点']"
            >
                <template v-slot:append>
                    <q-icon 
                        name="place" 
                        class="cursor-pointer" 
                        :color="selectingEnd ? 'primary' : ''"
                        @click="$emit('toggle-select-end')"
                    >
                        <q-tooltip>在地图上选点</q-tooltip>
                    </q-icon>
                </template>
            </q-input>
         </div>
      </div>

      <q-select
        filled
        dense
        v-model="form.strategy"
        :options="strategyOptions"
        label="选路策略"
        emit-value
        map-options
      />

      <div class="row justify-end">
        <q-btn 
            label="开始规划" 
            type="submit" 
            color="primary" 
            :loading="loading" 
            class="full-width"
            icon="directions"
        />
      </div>
    </q-form>

    <!-- Result Display -->
    <q-slide-transition>
        <div v-if="routeResult" class="q-mt-lg">
            <q-separator class="q-mb-md" />
            <div class="text-subtitle1 q-mb-sm text-weight-bold">规划结果</div>
            <q-list bordered separator class="rounded-borders">
                <q-item>
                    <q-item-section avatar>
                        <q-icon name="straighten" color="primary" />
                    </q-item-section>
                    <q-item-section>
                        <q-item-label caption>总距离</q-item-label>
                        <q-item-label>{{ (routeResult.distance / 1000).toFixed(1) }} km</q-item-label>
                    </q-item-section>
                </q-item>
                
                <q-item>
                    <q-item-section avatar>
                        <q-icon name="schedule" color="primary" />
                    </q-item-section>
                    <q-item-section>
                        <q-item-label caption>预计耗时</q-item-label>
                        <q-item-label>{{ formatDuration(routeResult.duration) }}</q-item-label>
                    </q-item-section>
                </q-item>

                <q-item v-if="routeResult.toll_distance > 0">
                    <q-item-section avatar>
                        <q-icon name="paid" color="orange" />
                    </q-item-section>
                    <q-item-section>
                        <q-item-label caption>收费路段</q-item-label>
                        <q-item-label>{{ (routeResult.toll_distance / 1000).toFixed(1) }} km</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </div>
    </q-slide-transition>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const props = defineProps({
  loading: Boolean,
  selectingStart: Boolean,
  selectingEnd: Boolean,
  routeResult: Object
})

const emit = defineEmits(['plan-route', 'toggle-select-start', 'toggle-select-end'])

const form = reactive({
  origin: '福建省三明厦钨新能源',
  destination: '福建省平潭跨境电商园',
  strategy: 0
})

const strategyOptions = [
  { label: '速度优先', value: 0 },
  { label: '费用优先', value: 1 },
  { label: '距离优先', value: 2 }
]

const formatDuration = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}小时${m}分钟`
    return `${m}分钟`
}

const onSubmit = () => {
  emit('plan-route', { ...form })
}

const setAddress = (type, val) => {
    if (type === 'start') form.origin = val
    if (type === 'end') form.destination = val
}

defineExpose({ setAddress })
</script>
