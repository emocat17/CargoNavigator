<template>
  <div class="q-pa-md">
    <div class="text-subtitle1 q-mb-sm text-weight-bold row items-center">
        <q-icon name="list_alt" class="q-mr-sm" />
        规划结果详情
        <q-space />
        <q-btn flat round dense icon="close" @click="$emit('close')" />
    </div>
    
    <!-- Fatigue Warning -->
    <q-banner v-if="routeResult.duration > 14400" rounded class="bg-red-1 text-red-9 q-mb-sm dense">
      <template v-slot:avatar>
        <q-icon name="warning" color="red" />
      </template>
      <div class="text-caption text-weight-bold">长途驾驶提醒：预计车程超过4小时，请注意休息。</div>
    </q-banner>

    <!-- Night Driving Warning -->
    <q-banner v-if="routeResult.tags && routeResult.tags.includes('夜间行车')" rounded class="bg-indigo-1 text-indigo-10 q-mb-sm dense">
      <template v-slot:avatar>
        <q-icon name="nights_stay" color="indigo" />
      </template>
      <div class="text-caption text-weight-bold">夜间行车提醒：预计行程包含深夜时段(2:00-5:00)，视线不佳请减速慢行。</div>
    </q-banner>

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
            <div class="row q-gutter-x-md q-mt-sm text-caption text-grey-7 wrap">
                <div v-if="routeResult.total_cost" class="row items-center text-teal-9 text-weight-bold">
                    <q-icon name="payments" class="q-mr-xs"/> 总成本 ¥{{ routeResult.total_cost.toFixed(0) }} 
                    <q-tooltip content-class="bg-teal text-white">
                        含油费估算 ¥{{ routeResult.estimated_fuel_cost }} + 路费 ¥{{ routeResult.toll_cost }}
                    </q-tooltip>
                </div>
                <div v-if="routeResult.traffic_lights" class="row items-center"><q-icon name="traffic" class="q-mr-xs"/> {{ routeResult.traffic_lights }}红绿灯</div>
                <div v-if="routeResult.toll_cost" class="row items-center"><q-icon name="paid" class="q-mr-xs"/> 路费 ¥{{ routeResult.toll_cost }}</div>
                <div v-if="routeResult.traffic_condition" class="row items-center"><q-icon name="assessment" class="q-mr-xs"/> {{ routeResult.traffic_condition }}</div>
                <!-- New Tunnel Info -->
                <div v-if="routeResult.tunnel_count > 0" class="row items-center text-brown-8 text-weight-medium">
                    <q-icon name="landscape" class="q-mr-xs" /> 隧道{{ routeResult.tunnel_count }}个 ({{ (routeResult.tunnel_distance / 1000).toFixed(1) }}km)
                </div>
            </div>
        </q-card-section>
    </q-card>

    <!-- 途经城市 -->
    <div v-if="routeResult.passed_cities && routeResult.passed_cities.length" class="q-mb-sm">
        <q-expansion-item
            expand-separator
            icon="location_city"
            label="途经城市"
            header-class="text-primary bg-grey-1 text-subtitle1"
            default-opened
        >
            <q-card>
                <q-card-section class="q-pa-sm">
                    <div class="row q-gutter-xs">
                        <q-chip v-for="city in routeResult.passed_cities" :key="city" size="md" color="blue-1" text-color="primary" class="q-ma-none q-mr-xs q-mb-xs">
                            {{ city }}
                        </q-chip>
                    </div>
                </q-card-section>
            </q-card>
        </q-expansion-item>
    </div>

    <!-- 收费详情 -->
    <div v-if="routeResult.toll_roads_details && routeResult.toll_roads_details.length" class="q-mb-sm">
        <q-expansion-item
            expand-separator
            icon="toll"
            label="收费详情"
            header-class="text-orange-9 bg-orange-1 text-subtitle1"
        >
            <q-card>
                <q-card-section class="q-pa-xs">
                    <q-list separator>
                        <q-item v-for="(toll, idx) in routeResult.toll_roads_details" :key="idx" class="q-py-xs">
                            <q-item-section avatar style="min-width: 24px">
                                <q-icon name="paid" size="sm" color="orange" />
                            </q-item-section>
                            <q-item-section>
                                <q-item-label class="text-body2 text-grey-9">{{ toll }}</q-item-label>
                            </q-item-section>
                        </q-item>
                    </q-list>
                </q-card-section>
            </q-card>
        </q-expansion-item>
    </div>

    <div class="text-subtitle1 q-mb-xs q-pl-xs text-grey-7">导航详情</div>

    <q-scroll-area style="height: calc(100vh - 300px);" class="bg-white rounded-borders border-grey-3">
        <q-list separator>
            <q-item class="bg-grey-2">
                <q-item-section avatar>
                    <q-icon name="my_location" color="blue" size="md" />
                </q-item-section>
                <q-item-section>
                    <q-item-label class="text-weight-bold text-subtitle1">起点</q-item-label>
                </q-item-section>
            </q-item>

            <q-item v-for="(step, index) in routeResult.steps" :key="index" class="q-py-md" :class="getTrafficBg(step.traffic_status)">
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
    </q-scroll-area>
  </div>
</template>

<script setup>
const props = defineProps({
  routeResult: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

const formatDuration = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}小时${m}分钟`
    return `${m}分钟`
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
    if (a.includes('靠左')) return 'subdirectory_arrow_left'
    if (a.includes('靠右')) return 'subdirectory_arrow_right'
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
    // Check if step involves a tunnel based on keyword heuristics
    if (!step) return false;
    const road = step.road || '';
    const instruction = step.instruction || '';
    const action = step.assistant_action || '';
    return road.includes('隧道') || instruction.includes('隧道') || action.includes('隧道');
}

const isLongTunnel = (step) => {
    // Determine if it is a "Long Tunnel" (e.g. > 3000m)
    return isTunnel(step) && step.distance > 3000;
}
</script>
