<template>
  <div class="q-pa-md">
    <div class="text-h6 q-mb-md">路线对比分析</div>

    <!-- Summary cards -->
    <div class="row q-col-gutter-md q-mb-md">
      <div v-for="(route, idx) in routes" :key="idx" class="col-12 col-md-6">
        <q-card
          flat bordered
          :class="{'bg-green-1': idx===recommendedIndex, 'cursor-pointer': true}"
          @click="$emit('select-route', idx)"
        >
          <q-card-section>
            <div class="row items-center">
              <div class="text-subtitle1 text-weight-bold">方案 {{ idx+1 }}</div>
              <q-space />
              <q-badge v-if="idx===recommendedIndex" color="green" label="推荐" />
              <q-badge v-else-if="idx===0" color="primary" label="最短" />
              <q-badge v-if="route.riskLevel" :color="riskColor(route.riskLevel)" :label="route.riskLevel" class="q-ml-xs" />
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section class="q-pa-sm">
            <div class="row q-col-gutter-xs text-center">
              <div class="col-3">
                <div class="text-caption text-grey-6">距离</div>
                <div class="text-subtitle2 text-weight-bold">{{ (route.distance/1000).toFixed(0) }}km</div>
              </div>
              <div class="col-3">
                <div class="text-caption text-grey-6">耗时</div>
                <div class="text-subtitle2 text-weight-bold">{{ fmtDuration(route.duration) }}</div>
              </div>
              <div class="col-3">
                <div class="text-caption text-grey-6">过路费</div>
                <div class="text-subtitle2 text-weight-bold">{{ route.toll_cost?.toFixed(0)||'--' }}</div>
              </div>
              <div class="col-3">
                <div class="text-caption text-grey-6">评分</div>
                <div class="text-subtitle2 text-weight-bold" :class="scoreColor(route.score)">{{ route.score??'--' }}/10</div>
              </div>
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section class="q-pa-sm">
            <div class="row q-col-gutter-xs">
              <div class="col-4">
                <q-chip dense size="sm" :color="route.riskyBridges>0?'red':'green'" text-color="white" icon="engineering">
                  桥梁 {{ route.safeBridges||0 }}/{{ route.totalBridges||0 }}
                </q-chip>
              </div>
              <div class="col-4">
                <q-chip dense size="sm" :color="route.constructionCount>0?'orange':'green'" text-color="white" icon="warning">
                  施工 {{ route.constructionCount||0 }}
                </q-chip>
              </div>
              <div class="col-4">
                <q-chip dense size="sm" :color="route.dimensionsOk?'green':'red'" text-color="white" icon="check_circle">
                  尺寸 {{ route.dimensionsOk ? '通过' : '警告' }}
                </q-chip>
              </div>
            </div>
          </q-card-section>
          <q-card-section v-if="route.description" class="q-pa-sm">
            <div class="text-caption text-grey-7">{{ route.description }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Comparison Table -->
    <q-table
      :rows="tableRows"
      :columns="tableColumns"
      row-key="index"
      dense
      flat bordered
      hide-bottom
      :pagination="{rowsPerPage: 10}"
    >
      <template v-slot:body-cell-name="props">
        <q-td :props="props">
          <div class="row items-center">
            <q-badge v-if="props.row.index===recommendedIndex" color="green" label="推荐" class="q-mr-xs" />
            {{ props.value }}
          </div>
        </q-td>
      </template>
      <template v-slot:body-cell-risk="props">
        <q-td :props="props">
          <q-badge :color="riskColor(props.value)" :label="props.value" />
        </q-td>
      </template>
      <template v-slot:body-cell-score="props">
        <q-td :props="props">
          <div class="row items-center">
            <q-linear-progress :value="(props.value||0)/10" :color="scoreColor(props.value)" style="width:60px;" class="q-mr-sm" rounded />
            {{ props.value }}
          </div>
        </q-td>
      </template>
    </q-table>

    <div class="row q-mt-md justify-center">
      <q-btn outline color="primary" icon="route" label="在地图上查看" @click="$emit('close')" class="q-mr-sm" />
      <q-btn outline color="grey" icon="close" label="关闭" @click="$emit('close')" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  routes: { type: Array, default: () => [] },
  assessmentResults: { type: Array, default: () => [] },
  recommendedIndex: { type: Number, default: 0 },
})
defineEmits(['select-route', 'close'])

const riskColor = level => ({'低':'green','中':'orange','高':'red','极高':'deep-orange'}[level]||'grey')
const scoreColor = s => s>=7?'green':s>=4?'orange':'red'
const fmtDuration = s => {
  if (!s) return '--'
  const h=Math.floor(s/3600), m=Math.floor(s%3600/60)
  return h>0?`${h}时${m}分`:`${m}分钟`
}

const tableColumns = [
  {name:'name', label:'方案', field:'name', align:'left'},
  {name:'distance', label:'距离', field:'distance', align:'center', format:v=>`${(v/1000).toFixed(0)}km`},
  {name:'duration', label:'耗时', field:'duration', align:'center', format:v=>fmtDuration(v)},
  {name:'toll', label:'过路费', field:'toll', align:'center', format:v=>v!=null?`¥${v}`:'--'},
  {name:'bridges', label:'桥梁', field:'bridges', align:'center'},
  {name:'construction', label:'施工', field:'construction', align:'center'},
  {name:'risk', label:'风险等级', field:'risk', align:'center'},
  {name:'score', label:'评分', field:'score', align:'center'},
]

const tableRows = computed(() => props.routes.map((r, i) => {
  const a = props.assessmentResults[i] || {}
  const struct = a.route_compatibility?.structural_safety || {}
  return {
    index: i,
    name: `方案 ${i+1}`,
    distance: r.distance || 0,
    duration: r.duration || 0,
    toll: r.toll_cost || 0,
    bridges: `${struct.high_risk_bridges||0}风险/${struct.total_bridges||0}总计`,
    construction: a.traffic_analysis?.construction_impacts?.length || 0,
    risk: a.overall_assessment?.risk_level || '--',
    score: a.overall_assessment?.score,
  }
}))
</script>
