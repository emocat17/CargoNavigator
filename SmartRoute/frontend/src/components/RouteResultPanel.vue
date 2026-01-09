<template>
  <div class="q-pa-md column full-height">
    <div class="text-subtitle1 q-mb-sm text-weight-bold row items-center col-auto">
        <q-icon name="alt_route" class="q-mr-sm" />
        规划方案 ({{ routes.length }})
        <q-space />
        <q-btn flat round dense icon="close" @click="$emit('close')" />
    </div>
    
    <!-- Route List Selection -->
    <div class="col-auto q-mb-md">
      <!-- Export Action -->
      <div v-if="enableExport" class="row justify-end q-mb-sm">
        <q-btn 
            color="secondary" 
            icon="file_download" 
            label="导出方案数据" 
            size="sm" 
            outline 
            @click="handleExportData"
        >
            <q-tooltip>导出选中路线及车辆参数为 JSON 文件</q-tooltip>
        </q-btn>
      </div>

      <q-list bordered separator class="rounded-borders">
        <q-item 
          v-for="(route, index) in routes" 
          :key="index"
          clickable
          v-ripple
          :active="index === selectedIndex"
          active-class="bg-blue-1 text-primary"
          @click="$emit('select-route', index)"
        >
          <q-item-section avatar>
            <q-badge :color="index === 0 ? 'red' : 'blue'" :label="index === 0 ? '推荐' : `方案${index+1}`" />
          </q-item-section>

          <q-item-section>
            <q-item-label class="text-weight-bold">{{ formatDuration(route.duration) }}</q-item-label>
            <q-item-label caption>
              {{ (route.distance / 1000).toFixed(1) }}km | ¥{{ route.total_cost.toFixed(0) }}
            </q-item-label>
          </q-item-section>

          <q-item-section side>
            <div class="row q-gutter-xs justify-end" style="max-width: 120px; flex-wrap: wrap;">
               <q-badge v-for="tag in (route.tags || []).slice(0, 2)" :key="tag" color="teal" outline :label="tag" class="q-mb-xs" />
               <q-badge v-if="(route.tags || []).length > 2" color="teal" outline label="..." />
            </div>
          </q-item-section>
        </q-item>
      </q-list>
    </div>

    <q-separator class="q-mb-sm" />

    <!-- Detail View Area -->
    <div class="col column" style="overflow: hidden;" v-if="selectedRoute">
        <!-- Warnings -->
        <div class="col-auto q-mb-sm">
            <q-banner v-if="selectedRoute.duration > 14400" rounded class="bg-red-1 text-red-9 q-mb-xs dense">
            <template v-slot:avatar>
                <q-icon name="warning" color="red" />
            </template>
            <div class="text-caption text-weight-bold">长途驾驶提醒：预计车程超过4小时，请注意休息。</div>
            </q-banner>

            <q-banner v-if="selectedRoute.tags && selectedRoute.tags.includes('夜间行车')" rounded class="bg-indigo-1 text-indigo-10 q-mb-xs dense">
            <template v-slot:avatar>
                <q-icon name="nights_stay" color="indigo" />
            </template>
            <div class="text-caption text-weight-bold">夜间行车提醒：预计行程包含深夜时段(2:00-5:00)，视线不佳请减速慢行。</div>
            </q-banner>
        </div>

        <q-scroll-area class="col bg-white rounded-borders border-grey-3">
            <div class="q-pa-sm">
                <!-- Detailed Stats Card -->
                <q-card flat bordered class="bg-blue-1 text-primary q-mb-sm">
                    <q-card-section class="q-pa-sm">
                        <!-- Route Description / Key Points -->
                        <div v-if="selectedRoute.route_description" class="text-subtitle2 text-weight-bold text-black q-mb-xs">
                            <q-icon name="map" class="q-mr-xs text-primary"/>
                            {{ selectedRoute.route_description }}
                        </div>
                        <div v-else-if="selectedRoute.major_roads && selectedRoute.major_roads.length" class="text-subtitle1 text-weight-bold ellipsis-2-lines q-mb-xs text-black">
                            {{ selectedRoute.major_roads.join(' > ') }}
                        </div>

                        <div class="row q-gutter-x-md q-mt-sm text-caption text-grey-7 wrap">
                            <div v-if="selectedRoute.total_cost" class="row items-center text-teal-9 text-weight-bold">
                                <q-icon name="payments" class="q-mr-xs"/> 预估总费用 ¥{{ selectedRoute.total_cost.toFixed(0) }} 
                                <q-tooltip content-class="bg-teal text-white">
                                    含油费估算 ¥{{ selectedRoute.estimated_fuel_cost }} + 路费 ¥{{ selectedRoute.toll_cost }}
                                </q-tooltip>
                            </div>
                            <div v-if="selectedRoute.traffic_lights" class="row items-center"><q-icon name="traffic" class="q-mr-xs"/> {{ selectedRoute.traffic_lights }}红绿灯</div>
                            <div v-if="selectedRoute.toll_cost" class="row items-center"><q-icon name="paid" class="q-mr-xs"/> 仅路费 ¥{{ selectedRoute.toll_cost }}</div>
                            <div v-if="selectedRoute.traffic_condition" class="row items-center"><q-icon name="assessment" class="q-mr-xs"/> {{ selectedRoute.traffic_condition }}</div>
                            <!-- New Tunnel Info -->
                            <div v-if="selectedRoute.tunnel_count > 0" class="row items-center text-brown-8 text-weight-medium">
                                <q-icon name="landscape" class="q-mr-xs" /> 隧道{{ selectedRoute.tunnel_count }}个 (隧道总长 {{ (selectedRoute.tunnel_distance / 1000).toFixed(1) }}km)
                            </div>
                        </div>
                    </q-card-section>
                </q-card>

                <!-- 途经城市 -->
                <div v-if="selectedRoute.passed_cities && selectedRoute.passed_cities.length" class="q-mb-sm">
                    <q-expansion-item
                        expand-separator
                        icon="location_city"
                        label="途经城市"
                        header-class="text-primary bg-grey-1 text-subtitle1"
                        dense
                    >
                        <q-card>
                            <q-card-section class="q-pa-sm">
                                <div class="row q-gutter-xs">
                                    <q-chip v-for="city in selectedRoute.passed_cities" :key="city" size="sm" color="blue-1" text-color="primary" class="q-ma-none q-mr-xs q-mb-xs">
                                        {{ city }}
                                    </q-chip>
                                </div>
                            </q-card-section>
                        </q-card>
                    </q-expansion-item>
                </div>

                <!-- 收费详情 -->
                <div v-if="selectedRoute.toll_roads_details && selectedRoute.toll_roads_details.length" class="q-mb-sm">
                    <q-expansion-item
                        expand-separator
                        icon="toll"
                        label="收费详情"
                        header-class="text-orange-9 bg-orange-1 text-subtitle1"
                        dense
                    >
                        <q-card>
                            <q-card-section class="q-pa-xs">
                                <q-list separator dense>
                                    <q-item v-for="(toll, idx) in selectedRoute.toll_roads_details" :key="idx" class="q-py-xs">
                                        <q-item-section avatar style="min-width: 24px">
                                            <q-icon name="paid" size="xs" color="orange" />
                                        </q-item-section>
                                        <q-item-section>
                                            <q-item-label class="text-caption text-grey-9">{{ toll }}</q-item-label>
                                        </q-item-section>
                                    </q-item>
                                </q-list>
                            </q-card-section>
                        </q-card>
                    </q-expansion-item>
                </div>

                <div class="text-subtitle1 q-mb-xs q-pl-xs text-grey-7">导航详情</div>

                <q-list separator dense>
                    <q-item class="bg-grey-2">
                        <q-item-section avatar>
                            <q-icon name="my_location" color="blue" size="md" />
                        </q-item-section>
                        <q-item-section>
                            <q-item-label class="text-weight-bold text-subtitle1">起点</q-item-label>
                        </q-item-section>
                    </q-item>

                    <q-item v-for="(step, index) in selectedRoute.steps" :key="index" class="q-py-md" :class="getTrafficBg(step.traffic_status)">
                        <q-item-section avatar top class="column items-center q-pt-xs">
                            <q-icon :name="getActionIcon(step.action)" color="grey-8" size="md" class="q-mb-xs"/>
                            <q-badge v-if="step.traffic_status && step.traffic_status !== '未知'" rounded :color="getTrafficColor(step.traffic_status)" :label="step.traffic_status" class="text-xs" style="transform: scale(0.9);"/>
                        </q-item-section>
                        
                        <q-item-section>
                            <q-item-label class="text-subtitle1">
                                {{ step.instruction }}
                                <q-badge v-if="isTunnel(step)" color="brown" label="隧道" class="q-ml-sm" outline size="sm" />
                            </q-item-label>
                            <q-item-label caption v-if="step.road" class="text-primary text-weight-medium q-mt-xs text-body2 row items-center">
                                <q-icon name="place" size="xs" class="q-mr-xs" />{{ step.road }}
                            </q-item-label>
                            <!-- Assistant Action -->
                            <q-item-label caption v-if="step.assistant_action" class="text-orange-9 text-weight-medium q-mt-xs text-body2 row items-center">
                                <q-icon name="info_outline" size="xs" class="q-mr-xs" />{{ step.assistant_action }}
                            </q-item-label>
                        </q-item-section>
                        
                        <q-item-section side top>
                            <q-item-label caption class="text-body2">{{ step.distance }}米</q-item-label>
                        </q-item-section>
                    </q-item>
                    
                    <q-item class="bg-grey-2">
                        <q-item-section avatar>
                            <q-icon name="place" color="red" size="md" />
                        </q-item-section>
                        <q-item-section>
                            <q-item-label class="text-weight-bold text-subtitle1">终点</q-item-label>
                        </q-item-section>
                    </q-item>
                </q-list>
            </div>
        </q-scroll-area>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useQuasar } from 'quasar'

const props = defineProps({
  routes: {
    type: Array,
    required: true,
    default: () => []
  },
  selectedIndex: {
    type: Number,
    default: 0
  },
  vehicle: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'select-route'])
const $q = useQuasar()

const enableExport = import.meta.env.VITE_ENABLE_DATA_EXPORT === 'true'

const selectedRoute = computed(() => {
    if (!props.routes || props.routes.length === 0) return null
    return props.routes[props.selectedIndex] || props.routes[0]
})

const formatDuration = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}小时${m}分钟`
    return `${m}分钟`
}

const handleExportData = () => {
    if (!selectedRoute.value) return

    const exportData = {
        exported_at: new Date().toISOString(),
        vehicle_profile: props.vehicle,
        route_summary: {
            strategy: selectedRoute.value.strategy,
            tags: selectedRoute.value.tags,
            distance_km: (selectedRoute.value.distance / 1000).toFixed(2),
            duration_min: Math.floor(selectedRoute.value.duration / 60),
            toll_cost: selectedRoute.value.toll_cost,
            fuel_cost: selectedRoute.value.estimated_fuel_cost,
            total_cost: selectedRoute.value.total_cost,
            tunnel_count: selectedRoute.value.tunnel_count,
            traffic_lights: selectedRoute.value.traffic_lights
        },
        route_details: selectedRoute.value
    }

    const jsonStr = JSON.stringify(exportData, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const a = document.createElement('a')
    a.href = url
    a.download = `route_export_${new Date().getTime()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    $q.notify({
        type: 'positive',
        message: '数据已导出',
        icon: 'file_download'
    })
}

const getActionIcon = (action) => {
    if (!action) return 'navigation'
    const a = action.toString()
    if (a.includes('左转')) return 'turn_left'
    if (a.includes('右转')) return 'turn_right'
    if (a.includes('向左前方')) return 'turn_slight_left'
    if (a.includes('向右前方')) return 'turn_slight_right'
    if (a.includes('掉头')) return 'u_turn_left'
    if (a.includes('直行')) return 'straight'
    if (a.includes('靠左')) return 'turn_slight_left'
    if (a.includes('靠右')) return 'turn_slight_right'
    return 'navigation'
}

const getTrafficColor = (status) => {
    if (status === '拥堵') return 'red'
    if (status === '缓行') return 'orange'
    if (status === '畅通') return 'green'
    return 'grey'
}

const getTrafficBg = (status) => {
    if (status === '拥堵') return 'bg-red-1'
    if (status === '缓行') return 'bg-orange-1'
    return ''
}

const isTunnel = (step) => {
    return step.road && (step.road.includes('隧道') || step.instruction.includes('隧道'))
}
</script>
