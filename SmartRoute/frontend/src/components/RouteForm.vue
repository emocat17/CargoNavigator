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

      <q-select
        filled
        v-model="form.strategy"
        :options="strategyOptions"
        label="选路策略"
        emit-value
        map-options
        input-style="font-size: 1.25rem"
        label-style="font-size: 1.1rem"
        popup-content-style="font-size: 1.1rem"
      >
        <template v-slot:option="scope">
          <q-item v-bind="scope.itemProps">
            <q-item-section>
              <q-item-label style="font-size: 1.1rem">{{ scope.opt.label }}</q-item-label>
            </q-item-section>
          </q-item>
        </template>
      </q-select>

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

    <!-- Result Display -->
    <q-slide-transition>
        <div v-if="routeResult" class="q-mt-lg relative-position">
            
            <!-- Header Card -->
            <q-card flat bordered class="bg-blue-1 text-primary q-mb-sm">
                <q-card-section class="q-pa-sm">
                    <div v-if="routeResult.major_roads && routeResult.major_roads.length" class="text-subtitle1 text-weight-bold ellipsis-2-lines q-mb-xs text-black">
                        {{ routeResult.major_roads.join(' > ') }}
                    </div>
                    <div class="row items-center q-gutter-x-sm text-body2">
                         <div class="text-weight-bold text-primary">{{ formatDuration(routeResult.duration) }}</div>
                         <div class="text-grey-8">({{ (routeResult.distance / 1000).toFixed(1) }}公里)</div>
                         <div class="text-grey-6">|</div>
                         <div class="text-primary">{{ routeResult.strategy }}</div>
                    </div>
                    <div class="row q-gutter-x-md q-mt-sm text-caption text-grey-7">
                        <div v-if="routeResult.traffic_lights"><q-icon name="traffic" /> {{ routeResult.traffic_lights }}红绿灯</div>
                        <div v-if="routeResult.toll_cost"><q-icon name="paid" /> ¥{{ routeResult.toll_cost }}</div>
                        <div v-if="routeResult.traffic_condition"><q-icon name="assessment" /> {{ routeResult.traffic_condition }}</div>
                    </div>
                </q-card-section>
            </q-card>

            <!-- Navigation List Header -->
            <div class="text-subtitle2 q-mb-xs q-pl-xs text-grey-7">导航详情</div>

            <!-- Scrollable Steps List -->
            <q-scroll-area style="height: 400px; max-height: 50vh;" class="bg-white rounded-borders border-grey-3">
                <q-list separator>
                    <q-item class="bg-grey-2">
                        <q-item-section avatar>
                            <q-icon name="my_location" color="blue" />
                        </q-item-section>
                        <q-item-section>
                            <q-item-label class="text-weight-bold">起点</q-item-label>
                        </q-item-section>
                    </q-item>

                    <q-item v-for="(step, index) in routeResult.steps" :key="index" class="q-py-md">
                        <q-item-section avatar top>
                            <q-icon :name="getActionIcon(step.action)" color="grey-8" size="sm" />
                        </q-item-section>
                        
                        <q-item-section>
                            <q-item-label class="text-body1">{{ step.instruction }}</q-item-label>
                            <q-item-label caption v-if="step.road" class="text-primary text-weight-medium q-mt-xs">
                                {{ step.road }}
                            </q-item-label>
                        </q-item-section>
                        
                        <q-item-section side top>
                            <q-item-label caption>{{ step.distance }}米</q-item-label>
                        </q-item-section>
                    </q-item>
                    
                    <q-item class="bg-grey-2">
                        <q-item-section avatar>
                            <q-icon name="place" color="red" />
                        </q-item-section>
                        <q-item-section>
                            <q-item-label class="text-weight-bold">终点</q-item-label>
                        </q-item-section>
                    </q-item>
                </q-list>
            </q-scroll-area>
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

const onSubmit = () => {
  emit('plan-route', { ...form })
}

const setAddress = (type, val) => {
    if (type === 'start') form.origin = val
    if (type === 'end') form.destination = val
}

defineExpose({ setAddress })
</script>
