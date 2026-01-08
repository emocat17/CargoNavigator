<template>
  <div class="q-pa-md">
    <div class="text-subtitle1 q-mb-sm text-weight-bold row items-center">
        <q-icon name="list_alt" class="q-mr-sm" />
        规划结果详情
        <q-space />
        <q-btn flat round dense icon="close" @click="$emit('close')" />
    </div>
    
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

    <!-- 途经城市 -->
    <div v-if="routeResult.passed_cities && routeResult.passed_cities.length" class="q-mb-sm">
        <q-expansion-item
            dense
            dense-toggle
            expand-separator
            icon="location_city"
            label="途经城市"
            header-class="text-primary bg-grey-1"
            default-opened
        >
            <q-card>
                <q-card-section class="q-pa-sm">
                    <div class="row q-gutter-xs">
                        <q-chip v-for="city in routeResult.passed_cities" :key="city" size="sm" color="blue-1" text-color="primary" class="q-ma-none q-mr-xs q-mb-xs">
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
            dense
            dense-toggle
            expand-separator
            icon="toll"
            label="收费详情"
            header-class="text-orange-9 bg-orange-1"
        >
            <q-card>
                <q-card-section class="q-pa-xs">
                    <q-list dense separator>
                        <q-item v-for="(toll, idx) in routeResult.toll_roads_details" :key="idx" dense class="q-py-xs">
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

    <div class="text-subtitle2 q-mb-xs q-pl-xs text-grey-7">导航详情</div>

    <q-scroll-area style="height: calc(100vh - 250px);" class="bg-white rounded-borders border-grey-3">
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
</script>
