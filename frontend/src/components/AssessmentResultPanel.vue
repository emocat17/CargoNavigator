<template>
  <div class="arp-root">
    <!-- ===== Loading Skeleton ===== -->
    <div v-if="assessing" class="arp-loading">
      <q-linear-progress indeterminate color="primary" class="q-mb-sm" />
      <q-card flat bordered class="bg-grey-1">
        <q-card-section class="q-pa-sm text-center">
          <q-spinner-dots size="sm" color="primary" />
          <span class="text-caption text-grey-7 q-ml-xs">正在分析路线安全性...</span>
          <div v-for="i in 3" :key="i" class="skeleton-line q-mt-sm"
            style="height:12px; border-radius:4px; background:#e2e8f0;" />
        </q-card-section>
      </q-card>
    </div>

    <!-- ===== Results Panel ===== -->
    <div v-if="!assessing && data" class="arp-results">
      <!-- ── Overall Verdict ── -->
      <q-card flat bordered class="verdict-card" :style="{ borderLeft: `4px solid ${riskBorderColor(overall.risk_level)}` }">
        <q-card-section class="q-pa-sm">
          <div class="row items-center q-col-gutter-sm">
            <!-- Score Circle -->
            <div class="col-auto">
              <div class="score-circle" :style="{ background: riskBgColor(overall.risk_level) }">
                <span class="score-number">{{ overall.score }}</span>
                <span class="score-max">/10</span>
              </div>
            </div>
            <!-- Verdict -->
            <div class="col">
              <div class="row items-center q-gutter-xs">
                <q-badge :color="riskBadgeColor(overall.risk_level)" :label="overall.risk_level + '风险'" />
                <q-badge :color="recoColor(overall.recommendation)" :label="overall.recommendation" />
                <q-badge v-if="meta.confidence_level" outline :color="confidenceColor(meta.confidence_level)"
                  :label="'置信度:' + meta.confidence_level" />
              </div>
            </div>
          </div>
          <!-- Key Factors -->
          <div v-if="overall.key_factors?.length" class="q-mt-sm">
            <div class="row q-gutter-xs">
              <q-chip v-for="(f, i) in overall.key_factors" :key="i" dense size="sm" color="grey-3" text-color="grey-8"
                :label="f" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ── Bridge Safety ── -->
      <q-expansion-item v-model="expanded.bridge" expand-separator dense header-class="bg-grey-2 text-weight-medium"
        class="q-mt-xs">
        <template #header>
          <q-icon name="landscape" :color="bridgeStatusIcon().color" size="xs" class="q-mr-sm" />
          <span class="text-caption text-weight-bold">桥梁安全分析</span>
          <q-space />
          <q-badge dense :color="bridgeStatusIcon().color" :label="bridgeSummary()" class="q-mr-sm" />
        </template>

        <q-card flat class="q-pa-sm">
          <!-- No bridge data -->
          <q-banner v-if="!structural.total_bridges" rounded class="bg-orange-1 q-mb-sm">
            <template #avatar><q-icon name="report_problem" color="orange" /></template>
            <span class="text-caption">桥梁数据库未覆盖该路线高速公路段，无法评估桥梁结构安全性。</span>
          </q-banner>

          <!-- Bridge stats -->
          <div v-if="structural.total_bridges" class="row q-col-gutter-xs text-center q-mb-sm">
            <div class="col-4"><div class="text-h6 text-primary">{{ structural.total_bridges }}</div><div class="text-caption text-grey-6">桥梁总数</div></div>
            <div class="col-4"><div class="text-h6 text-red">{{ structural.high_risk_bridges }}</div><div class="text-caption text-grey-6">高风险</div></div>
            <div class="col-4"><div class="text-h6 text-orange">{{ structural.max_moment_ratio?.toFixed(2) }}</div><div class="text-caption text-grey-6">最大效应比</div></div>
          </div>

          <!-- Safety assessment -->
          <div class="text-caption row items-center q-gutter-x-xs q-mb-sm">
            <q-icon :name="bridgeStatusIcon().icon" :color="bridgeStatusIcon().color" size="xs" />
            <span :class="bridgeStatusIcon().textClass">{{ structural.safety_assessment || '未知' }}</span>
          </div>

          <!-- Flags -->
          <div v-if="structural.escort_required" class="text-caption text-orange q-mb-xs">⚠ 需要护送车辆陪同</div>
          <div v-if="structural.reinforcement_needed" class="text-caption text-red q-mb-xs">🚫 桥梁需要临时加固</div>
          <div v-if="structural.route_max_speed_kmh != null && structural.route_max_speed_kmh > 0" class="text-caption text-grey-7">
            路线限速: ≤{{ structural.route_max_speed_kmh }}km/h
          </div>

          <!-- Bridge grades -->
          <div v-if="gradesEntries.length" class="q-mt-sm">
            <div class="text-caption text-grey-7 q-mb-xs">桥梁评级分布:</div>
            <div class="row q-gutter-xs">
              <q-badge v-for="(g, i) in gradesEntries" :key="i" dense :color="gradeColor(g[0])" :label="g[1]+'座 '+g[0]" />
            </div>
          </div>
        </q-card>
      </q-expansion-item>

      <!-- ── Construction & Traffic ── -->
      <q-expansion-item v-model="expanded.traffic" expand-separator dense header-class="bg-grey-2 text-weight-medium"
        class="q-mt-xs">
        <template #header>
          <q-icon name="construction" :color="traffic.hasImpacts ? 'orange' : 'green'" size="xs" class="q-mr-sm" />
          <span class="text-caption text-weight-bold">施工与交通影响</span>
          <q-space />
          <q-badge dense :color="traffic.hasImpacts ? 'orange' : 'green'"
            :label="traffic.hasImpacts ? traffic.impacts.length + '处施工' : '无施工影响'" class="q-mr-sm" />
        </template>

        <q-card flat class="q-pa-sm">
          <div class="text-caption text-grey-7 q-mb-xs">⏱ {{ traffic.estimated_time || '?' }}</div>

          <div v-if="traffic.hasImpacts">
            <q-list dense separator>
              <q-item v-for="(imp, i) in traffic.impacts" :key="i" class="q-pa-xs">
                <q-item-section>
                  <q-item-label class="text-caption" style="word-break:break-all;">{{ imp.location }}</q-item-label>
                  <q-item-label caption>
                    {{ imp.lane_occupancy }} · 延误{{ imp.delay_minutes }}分钟
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge dense :color="impactColor(imp.impact_level)" :label="imp.impact_level" />
                </q-item-section>
              </q-item>
            </q-list>
            <div class="text-caption text-grey-7 q-mt-sm">
              总计延误: {{ traffic.total_delay }}分钟
            </div>
          </div>
          <div v-else class="text-caption text-green">✅ 该路线无施工/交通事件影响</div>

          <div v-if="traffic.recommended_time_window" class="text-caption text-primary q-mt-sm">
            🕐 推荐通行时间: {{ traffic.recommended_time_window }}
          </div>
        </q-card>
      </q-expansion-item>

      <!-- ── Dimension Compliance ── -->
      <q-expansion-item v-model="expanded.dimension" expand-separator dense header-class="bg-grey-2 text-weight-medium"
        class="q-mt-xs">
        <template #header>
          <q-icon name="straighten" :color="dim.ok ? 'green' : 'red'" size="xs" class="q-mr-sm" />
          <span class="text-caption text-weight-bold">尺寸合规检查</span>
          <q-space />
          <q-badge dense :color="dim.ok ? 'green' : 'red'" :label="compliance || '?'" class="q-mr-sm" />
        </template>

        <q-card flat class="q-pa-sm">
          <div class="row q-col-gutter-xs text-center">
            <div class="col-4">
              <div class="text-caption text-grey-6">高度</div>
              <div class="text-body2">{{ dimCheck.vehicle_height || '?' }}m</div>
              <q-badge dense :color="dimCheck.height_status?.includes('通过') ? 'green' : 'red'"
                :label="dimCheck.height_status?.includes('通过') ? '✓' : '✗'" />
            </div>
            <div class="col-4">
              <div class="text-caption text-grey-6">重量</div>
              <div class="text-body2">{{ dimCheck.vehicle_weight || '?' }}t</div>
              <q-badge dense :color="dimCheck.weight_status?.includes('符合') ? 'green' : 'red'"
                :label="dimCheck.weight_status?.includes('符合') ? '✓' : '✗'" />
            </div>
            <div class="col-4">
              <div class="text-caption text-grey-6">限值</div>
              <div class="text-body2">H:{{ dimCheck.height_limit }}m</div>
              <div class="text-body2">W:{{ dimCheck.weight_limit }}t</div>
            </div>
          </div>
        </q-card>
      </q-expansion-item>

      <!-- ── Cost Estimation ── -->
      <q-expansion-item v-model="expanded.cost" expand-separator dense header-class="bg-grey-2 text-weight-medium"
        class="q-mt-xs">
        <template #header>
          <q-icon name="payments" color="primary" size="xs" class="q-mr-sm" />
          <span class="text-caption text-weight-bold">费用估算</span>
          <q-space />
          <span class="text-caption text-weight-bold text-primary q-mr-sm">¥{{ cost.total?.toFixed(0) || 0 }}</span>
        </template>

        <q-card flat class="q-pa-sm">
          <q-list dense separator>
            <q-item v-for="(v, k) in costBreakdown" :key="k" class="q-pa-xs">
              <q-item-section>
                <q-item-label class="text-caption">{{ v.label }}</q-item-label>
                <q-item-label caption>{{ v.note }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <span class="text-body2">¥{{ v.amount?.toFixed(0) || 0 }}</span>
              </q-item-section>
            </q-item>
          </q-list>
          <div class="text-caption text-grey-6 q-mt-sm">预计: {{ cost.estimated_days || 0 }}天</div>
          <div v-if="cost.warnings?.length" class="q-mt-xs">
            <div v-for="(w, i) in cost.warnings" :key="i" class="text-caption text-orange">⚠ {{ w }}</div>
          </div>
        </q-card>
      </q-expansion-item>

      <!-- ── Recommendations ── -->
      <q-expansion-item v-model="expanded.recommendations" expand-separator dense header-class="bg-grey-2 text-weight-medium"
        class="q-mt-xs">
        <template #header>
          <q-icon name="lightbulb" color="orange" size="xs" class="q-mr-sm" />
          <span class="text-caption text-weight-bold">建议与决策</span>
          <q-space />
          <q-badge dense :color="recoColor(overall.recommendation)" :label="approverDecision" class="q-mr-sm" />
        </template>

        <q-card flat class="q-pa-sm">
          <!-- Driver recommendations -->
          <div class="text-caption text-weight-bold q-mb-xs">🚛 驾驶员建议:</div>
          <ol class="rec-list">
            <li v-for="(r, i) in forUser" :key="'u'+i" class="text-caption">{{ r }}</li>
          </ol>

          <!-- Approver -->
          <div class="text-caption text-weight-bold q-mt-sm q-mb-xs">🏛 审批方决策:</div>
          <q-badge :color="recoColor(overall.recommendation)" :label="approverDecision" class="q-mb-sm" />
          <div v-if="specialConditions.length" class="q-mt-xs">
            <div v-for="(c, i) in specialConditions" :key="'sc'+i" class="text-caption text-grey-7">• {{ c }}</div>
          </div>
          <div v-if="riskNotes" class="text-caption text-orange q-mt-sm">⚠ {{ riskNotes }}</div>
        </q-card>
      </q-expansion-item>

      <!-- ── Metadata ── -->
      <q-expansion-item v-model="expanded.meta" expand-separator dense header-class="bg-grey-2 text-weight-medium"
        class="q-mt-xs">
        <template #header>
          <q-icon name="info" color="grey" size="xs" class="q-mr-sm" />
          <span class="text-caption text-weight-bold text-grey-7">评估元数据</span>
        </template>

        <q-card flat class="q-pa-sm">
          <div class="text-caption text-grey-7">📅 评估日期: {{ meta.assessment_date || '?' }}</div>
          <div class="text-caption text-grey-7 q-mt-xs">📊 数据源:
            <q-chip v-for="(src, i) in meta.data_sources || []" :key="i" dense size="sm" color="grey-3" :label="src" />
          </div>
          <div class="text-caption text-grey-7 q-mt-xs">🎯 置信度:
            <q-badge dense :color="confidenceColor(meta.confidence_level)" :label="meta.confidence_level || '?'" />
          </div>
        </q-card>
      </q-expansion-item>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'

const props = defineProps({
  assessment: { type: Object, default: null },
  assessing: { type: Boolean, default: false },
})

// ── Normalize data (handle both API wrapper {code, msg, data} and raw object) ──
const data = computed(() => props.assessment?.data || props.assessment || null)

// ── Section extractors ──
const overall = computed(() => data.value?.overall_assessment || {})
const traffic = computed(() => {
  const ta = data.value?.traffic_analysis || {}
  return {
    ...ta,
    hasImpacts: (ta.construction_impacts || []).length > 0,
    impacts: ta.construction_impacts || [],
  }
})
const structural = computed(() => data.value?.route_compatibility?.structural_safety || {})
const dimCheck = computed(() => data.value?.route_compatibility?.dimension_check || {})
const compliance = computed(() => data.value?.route_compatibility?.compliance_status || '')
const recs = computed(() => data.value?.recommendations || {})
const meta = computed(() => data.value?.metadata || {})
const cost = computed(() => data.value?.cost_estimate || {})

const forUser = computed(() => recs.value?.for_user || [])
const approverDecision = computed(() => recs.value?.for_approver?.approval_decision || '')
const specialConditions = computed(() => recs.value?.for_approver?.special_conditions || [])
const riskNotes = computed(() => recs.value?.for_approver?.risk_notes || '')

const dim = computed(() => ({
  ok: dimCheck.value.height_status?.includes('通过') && dimCheck.value.weight_status?.includes('符合'),
}))

const gradesEntries = computed(() => {
  const gs = structural.value?.bridge_grades_summary || {}
  return Object.entries(gs).filter(([k]) => k !== '未评估')
})

const costBreakdown = computed(() => {
  const bd = cost.value?.breakdown || {}
  const labels = {
    toll: { label: '过路费', note: '' },
    fuel: { label: '燃油费', note: '' },
    escort: { label: '护送费', note: '' },
    permit: { label: '许可费', note: '' },
    insurance: { label: '保险费', note: '' },
    labor: { label: '人工费', note: '' },
  }
  return Object.entries(bd).map(([k, v]) => ({
    key: k,
    label: labels[k]?.label || k,
    note: typeof v === 'object' ? (v.note || v.source || '') : '',
    amount: typeof v === 'object' ? (v.amount || 0) : (v || 0),
  }))
})

// ── Default expansion state ──
const expanded = reactive({
  bridge: true,
  traffic: true,
  dimension: false,
  cost: false,
  recommendations: false,
  meta: false,
})

// ── Bridge helpers ──
function bridgeSummary() {
  const t = structural.value.total_bridges || 0
  const r = structural.value.high_risk_bridges || 0
  if (!t) return '无桥梁数据'
  return `${t}桥/${r}风险`
}

function bridgeStatusIcon() {
  const s = structural.value
  if (!s.total_bridges) return { icon: 'help', color: 'grey', textClass: 'text-grey' }
  if (s.reinforcement_needed) return { icon: 'dangerous', color: 'red', textClass: 'text-red' }
  if (s.escort_required || s.high_risk_bridges > 0) return { icon: 'warning', color: 'orange', textClass: 'text-orange' }
  if ((s.max_moment_ratio || 0) >= 0.8) return { icon: 'info', color: 'orange', textClass: 'text-orange' }
  return { icon: 'check_circle', color: 'green', textClass: 'text-green' }
}

// ── Color helpers ──
function riskBorderColor(level) {
  return { '低': '#059669', '中': '#ea580c', '高': '#dc2626', '极高': '#991b1b' }[level] || '#888'
}
function riskBgColor(level) {
  return { '低': '#059669', '中': '#ea580c', '高': '#dc2626', '极高': '#991b1b' }[level] || '#888'
}
function riskBadgeColor(level) {
  return { '低': 'green', '中': 'orange', '高': 'red', '极高': 'deep-orange' }[level] || 'grey'
}
function recoColor(reco) {
  return { '推荐': 'green', '谨慎': 'orange', '不推荐': 'red' }[reco] || 'grey'
}
function confidenceColor(c) {
  return { '高': 'green', '中': 'orange', '低': 'red' }[c] || 'grey'
}
function impactColor(level) {
  return { '严重': 'red', '中等': 'orange', '轻微': 'yellow' }[level] || 'grey'
}
function gradeColor(g) {
  return {
    '安全通行': 'green', '完全安全通行': 'green', '正常通行': 'green',
    '条件通行': 'orange', '限速通行': 'orange', '建议限速': 'orange',
    '谨慎通行': 'red', '不建议通行': 'deep-orange',
  }[g] || 'grey'
}
</script>

<style scoped>
.arp-root { width: 100%; }

.verdict-card {
  border-radius: 8px;
  transition: border-left-color 0.3s;
}

.score-circle {
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: #fff; font-weight: bold;
}
.score-number { font-size: 18px; line-height: 1; }
.score-max { font-size: 9px; opacity: 0.8; }

.skeleton-line {
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.rec-list {
  margin: 0; padding-left: 18px;
}
.rec-list li {
  margin-bottom: 2px;
  line-height: 1.4;
}

.arp-results {
  max-height: 42vh;
  overflow-y: auto;
}
</style>
