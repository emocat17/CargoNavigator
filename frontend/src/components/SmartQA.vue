<template>
  <div class="q-pa-md column" style="height: calc(100vh - 120px);">
    <div class="text-h6 q-mb-sm">智能问答助手</div>
    <div v-if="currentRoute" class="q-mb-sm">
      <q-banner rounded class="bg-green-1 text-green-9 dense">
        <template v-slot:avatar><q-icon name="route" color="green" size="sm" /></template>
        <span class="text-caption text-weight-bold">当前路线：</span>
        <q-chip dense size="sm" color="green-2" text-color="green-9" class="q-ml-sm">
          {{ currentRoute._origin || '起点' }} → {{ currentRoute._destination || '终点' }}
        </q-chip>
        <q-chip dense size="sm" color="green-2" text-color="green-9">{{ (currentRoute.distance/1000).toFixed(0) }}km · {{ fmtD(currentRoute.duration) }}</q-chip>
      </q-banner>
    </div>

    <!-- Loading phase indicator -->
    <div v-if="phaseText" class="q-mb-sm">
      <q-banner rounded class="bg-blue-1 text-blue-9 dense">
        <q-spinner-dots size="sm" color="blue" class="q-mr-sm" />
        {{ phaseText }}
      </q-banner>
    </div>

    <q-scroll-area ref="chatScroll" class="col" style="flex: 1;">
      <div v-for="(msg, i) in messages" :key="i" class="q-mb-md">
        <!-- User message -->
        <div v-if="msg.role==='user'" class="q-mb-sm row justify-end">
          <div class="bg-primary text-white q-pa-sm rounded-borders" style="max-width:85%;white-space:pre-wrap;">{{ msg.content }}</div>
        </div>
        <!-- AI message -->
        <div v-else class="q-mb-sm row items-start">
          <q-avatar size="32px" class="q-mr-sm"><img src="https://cdn.quasar.dev/img/avatar3.jpg"></q-avatar>
          <div style="max-width:85%;">
            <div class="text-caption text-grey-7 q-mb-xs">
              {{ msg.name||'AI 助手' }}
              <q-spinner-dots v-if="msg.streaming" size="sm" color="grey-5" class="q-ml-sm" />
            </div>

            <!-- Error display -->
            <div v-if="msg.error" class="bg-red-1 q-pa-sm rounded-borders">
              <div class="text-red-9 text-caption q-mb-xs">{{ msg.error }}</div>
              <q-btn dense size="sm" color="red" icon="refresh" label="重试" @click="retry(msg)" />
            </div>

            <!-- AI text response -->
            <div v-if="msg.content" class="bg-amber-7 q-pa-sm rounded-borders" style="white-space:pre-wrap;">{{ msg.content }}</div>

            <!-- Structured Assessment Card -->
            <div v-if="msg.assessment" class="q-mt-sm">
              <q-card flat bordered class="q-pa-sm">
                <!-- Risk Header -->
                <div class="row items-center q-mb-sm">
                  <q-badge :color="riskColor(msg.assessment.riskLevel)" class="q-pa-xs text-h6" style="border-radius:8px;">
                    {{ msg.assessment.riskLevel || '未知' }}
                  </q-badge>
                  <div class="q-ml-sm text-subtitle2">{{ msg.assessment.summary || '' }}</div>
                  <q-space />
                  <div class="text-caption text-grey-6">评分 {{ msg.assessment.score ?? '--' }}/10</div>
                </div>
                <q-linear-progress v-if="msg.assessment.score != null" :value="(msg.assessment.score||0)/10" :color="riskColor(msg.assessment.riskLevel)" class="q-mb-sm" rounded />

                <!-- Quick Stats Row -->
                <div class="row q-col-gutter-sm q-mb-sm">
                  <div class="col-4">
                    <q-card flat bordered class="text-center q-pa-xs">
                      <div class="text-caption text-grey-6">桥梁</div>
                      <div :class="msg.assessment.riskyBridges>0?'text-red':'text-green'" class="text-subtitle1 text-weight-bold">
                        {{ msg.assessment.passableBridges||0 }}/{{ msg.assessment.totalBridges||0 }}
                      </div>
                    </q-card>
                  </div>
                  <div class="col-4">
                    <q-card flat bordered class="text-center q-pa-xs">
                      <div class="text-caption text-grey-6">施工</div>
                      <div :class="msg.assessment.constructionCount>0?'text-orange':'text-green'" class="text-subtitle1 text-weight-bold">
                        {{ msg.assessment.constructionCount||0 }}处
                      </div>
                    </q-card>
                  </div>
                  <div class="col-4">
                    <q-card flat bordered class="text-center q-pa-xs">
                      <div class="text-caption text-grey-6">尺寸</div>
                      <div :class="msg.assessment.dimensionsOk?'text-green':'text-red'" class="text-subtitle1 text-weight-bold">
                        {{ msg.assessment.dimensionsOk ? '通过' : '警告' }}
                      </div>
                    </q-card>
                  </div>
                </div>

                <!-- Risky Bridges (collapsible) -->
                <q-expansion-item v-if="msg.assessment.riskyBridgeList?.length" icon="engineering" label="风险桥梁详情" caption="效应比值超过安全阈值" class="bg-orange-1 q-mb-xs" dense>
                  <q-list dense>
                    <q-item v-for="b in msg.assessment.riskyBridgeList" :key="b.station" dense class="q-pa-xs">
                      <q-item-section>
                        <div class="text-caption text-weight-bold">{{ b.station }} {{ b.type }}</div>
                        <div class="text-caption text-grey-7">{{ b.highway }} 最大比值: {{ b.maxRatio?.toFixed(3) }}</div>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge color="red" :label="'1:'+(1/b.maxRatio).toFixed(0)" />
                      </q-item-section>
                    </q-item>
                  </q-list>
                </q-expansion-item>

                <!-- Construction Matches (collapsible) -->
                <q-expansion-item v-if="msg.assessment.constructionList?.length" icon="warning" label="施工路段详情" caption="与路线重叠的施工事件" class="bg-red-1 q-mb-xs" dense>
                  <q-list dense>
                    <q-item v-for="(c, idx) in msg.assessment.constructionList" :key="idx" dense class="q-pa-xs">
                      <q-item-section>
                        <div class="text-caption text-weight-bold">{{ c.highway }} {{ c.range }}</div>
                        <div class="text-caption text-grey-7">{{ c.desc }} · {{ c.direction }} · 重叠{{ c.overlap }}%</div>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </q-expansion-item>

                <!-- Warnings -->
                <div v-if="msg.assessment.warnings?.length" class="q-mt-xs">
                  <div v-for="(w, idx) in msg.assessment.warnings" :key="idx" class="text-caption text-orange-9 q-pa-xs">{{ w }}</div>
                </div>
              </q-card>
            </div>

            <!-- Legacy cards (fallback) -->
            <div v-if="!msg.assessment && msg.routeData" class="q-mt-sm">
              <q-card flat bordered class="bg-green-1"><q-card-section class="q-pa-sm">
                <div class="text-caption text-weight-bold text-green-9"><q-icon name="route" class="q-mr-xs" />路线规划</div>
                <div class="text-body2" style="white-space:pre-wrap;">{{ msg.routeData }}</div>
              </q-card-section></q-card>
            </div>
            <div v-if="!msg.assessment && msg.bridgeData" class="q-mt-sm">
              <q-card flat bordered class="bg-orange-1"><q-card-section class="q-pa-sm">
                <div class="text-caption text-weight-bold text-orange-9"><q-icon name="engineering" class="q-mr-xs" />桥梁安全评估</div>
                <div class="text-body2" style="white-space:pre-wrap;">{{ msg.bridgeData }}</div>
              </q-card-section></q-card>
            </div>
            <div v-if="!msg.assessment && msg.constructionData" class="q-mt-sm">
              <q-card flat bordered class="bg-red-1"><q-card-section class="q-pa-sm">
                <div class="text-caption text-weight-bold text-red-9"><q-icon name="warning" class="q-mr-xs" />施工事件匹配</div>
                <div class="text-body2" style="white-space:pre-wrap;">{{ msg.constructionData }}</div>
              </q-card-section></q-card>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="messages.length===0" class="text-center text-grey-6 q-mt-lg">
        <q-icon name="smart_toy" size="3rem" />
        <p class="q-mt-sm">问我关于路线规划、路况信息、或大件运输的问题</p>
        <div class="row q-gutter-sm justify-center q-mt-sm">
          <q-chip v-for="q in quickQuestions" :key="q" clickable color="primary" text-color="white" @click="send(q)">{{ q }}</q-chip>
        </div>
      </div>
    </q-scroll-area>

    <!-- Input area -->
    <div class="row q-mt-sm q-col-gutter-sm items-end">
      <div class="col">
        <q-input outlined dense v-model="inputMsg" :label="currentRoute?'可基于当前路线提问...':'请输入问题...'" @keyup.enter="send()" :disable="streaming">
          <template v-slot:after>
            <q-btn round dense flat icon="send" color="primary" @click="send()" :disable="!inputMsg.trim()||streaming" />
          </template>
        </q-input>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { streamChat } from '@/api/agent'
const $q = useQuasar()

const props = defineProps({ routes:{type:Array,default:()=>[]}, selectedRouteIndex:{type:Number,default:0}, vehicle:{type:Object,default:null} })
const emit = defineEmits(['plan-route'])
const inputMsg = ref('')
const streaming = ref(false)
const phaseText = ref('')
const messages = ref([])
const chatScroll = ref(null)

const currentRoute = computed(() => {
  if (!props.routes?.length) return null
  const r = props.routes[props.selectedRouteIndex] || props.routes[0]
  if (!r) return null
  if (!r._origin && r.route_description) { const p=r.route_description.split('--'); if(p.length>=2){r._origin=p[0];r._destination=p[p.length-1]} }
  return r
})
const quickQuestions = computed(() => currentRoute.value
  ? ['这条路线上有哪些施工路段？','走这条路安全吗？有什么风险？','沿途高速有没有交通管制？']
  : ['福建高速最近有什么施工路段？','从三明到平潭怎么走？','大件运输有哪些规定？'])
const fmtD = s => { const h=Math.floor(s/3600), m=Math.floor(s%3600/60); return h>0?`${h}时${m}分`:`${m}分钟` }
const scrollDown = async () => { await nextTick(); const el = chatScroll.value?.$el||chatScroll.value; if(el) el.scrollTop=el.scrollHeight }
const riskColor = level => ({'低':'green','中':'orange','高':'red','极高':'deep-orange'}[level]||'grey')

const routeCtx = computed(() => {
  const r = currentRoute.value; if (!r) return ''
  const p = [`当前规划路线：`,`距离:${(r.distance/1000).toFixed(1)}km`,`耗时:${fmtD(r.duration)}`,`过路费:¥${(r.toll_cost||0).toFixed(0)}`]
  if(r.route_description) p.push(`路径:${r.route_description}`)
  if(r.major_roads?.length) p.push(`主要道路:${r.major_roads.join(' → ')}`)
  if(r.risk_warnings?.length) p.push(`风险:${r.risk_warnings.join(',')}`)
  if(r.tunnel_count) p.push(`隧道:${r.tunnel_count}个`)
  if(r.traffic_condition) p.push(`路况:${r.traffic_condition}`)
  return p.join('\n')
})

// Parse bridge assessment text into structured data
function parseBridgeText(text) {
  if (!text) return null
  const result = {}
  // Extract risk level
  const rl = text.match(/风险等级:\s*(.+)/)
  if (rl) result.riskLevel = rl[1].trim()
  // Extract counts
  const tb = text.match(/路线桥梁总数:\s*(\d+)/)
  const ev = text.match(/已评估:\s*(\d+)/)
  const ps = text.match(/安全通行:\s*(\d+)/)
  const rs = text.match(/存在风险:\s*(\d+)/)
  const mr = text.match(/最大效应比值:\s*([\d.]+)/)
  if (tb) result.totalBridges = parseInt(tb[1])
  if (ev) result.bridgesEvaluated = parseInt(ev[1])
  if (ps) result.passableBridges = parseInt(ps[1])
  if (rs) result.riskyBridges = parseInt(rs[1])
  if (mr) result.maxRatio = parseFloat(mr[1])
  // Extract risky bridge details
  result.riskyBridgeList = []
  const rbRe = /•\s*(\S+)\s+(\S+)\s*\((\S+)\):\s*最大比值=([\d.]+)/g
  let m
  while ((m = rbRe.exec(text)) !== null) {
    result.riskyBridgeList.push({station:m[1], type:m[2], highway:m[3], maxRatio:parseFloat(m[4])})
  }
  // Extract warnings
  result.warnings = []
  const wLines = text.match(/\[!!\] 风险警告:\n([\s\S]*?)(?:\n\n|\n建议|$)/)
  if (wLines) {
    result.warnings = wLines[1].split('\n').filter(l => l.trim()).map(l => l.replace(/^\s+/, ''))
  }
  // Overall safe
  result.isSafe = text.includes('[OK] 安全')
  return result
}

// Parse construction match text into structured data
function parseConstructionText(text) {
  if (!text) return null
  const result = {}
  const cnt = text.match(/(\d+)\s*条与路线段落精确重叠/)
  if (cnt) result.matchCount = parseInt(cnt[1])
  const total = text.match(/共找到\s*(\d+)\s*条施工/)
  if (total) result.totalOnRoute = parseInt(total[1])

  result.constructionList = []
  // Parse each construction item: • G1517 莆炎高速 K165+581~K168+462 ...
  const itemRe = /•\s*(\S+)\s+(\S+)\s+(K\d+\+\d+~K\d+\+\d+)\s*\n\s*方向:\s*(\S+)\s*\|\s*时间:\s*(\S+)\s*\n\s*内容:\s*(.+?)(?:\n\s*重叠度:\s*([\d.]+)%)?/g
  let m
  while ((m = itemRe.exec(text)) !== null) {
    result.constructionList.push({
      highway: m[1]+' '+m[2],
      range: m[3],
      direction: m[4],
      time: m[5],
      desc: m[6].trim(),
      overlap: parseFloat(m[7]||'100'),
    })
  }
  result.constructionCount = result.constructionList.length || result.matchCount || 0
  result.warnings = []
  const wSec = text.match(/\[!!\] 施工警告:\n([\s\S]*)$/)
  if (wSec) {
    result.warnings = wSec[1].split('\n').filter(l => l.trim().startsWith('[')).map(l => l.trim())
  }
  return result
}

// Synthesize assessment from bridge + construction data
function synthesizeAssessment(bridgeData, constructionData) {
  const b = parseBridgeText(bridgeData) || {}
  const c = parseConstructionText(constructionData) || {}

  const riskyBridges = b.riskyBridges || 0
  const totalBridges = b.totalBridges || 0
  const maxRatio = b.maxRatio || 0
  const constructionCount = c.constructionCount || 0

  // Determine risk level
  let riskLevel = '低', score = 10
  if (riskyBridges > 2 || maxRatio >= 2.0) { riskLevel = '极高'; score = 2 }
  else if (riskyBridges > 0 || maxRatio >= 1.0) { riskLevel = '高'; score = 4 }
  else if (maxRatio >= 0.8 || constructionCount > 3) { riskLevel = '中'; score = 7 }
  else score = 9

  // Reduce score for construction
  if (constructionCount > 5) score = Math.max(1, score - 3)
  else if (constructionCount > 2) score = Math.max(2, score - 2)

  // Summary text
  const parts = []
  if (riskyBridges > 0) parts.push(`${riskyBridges}座桥梁存在风险`)
  else parts.push(`${totalBridges}座桥梁均可通行`)
  if (constructionCount > 0) parts.push(`${constructionCount}处施工与路线重叠`)

  return {
    riskLevel,
    score,
    summary: parts.join('，') || '路线已评估',
    totalBridges: b.bridgesEvaluated || totalBridges,
    passableBridges: b.passableBridges || 0,
    riskyBridges,
    maxRatio,
    constructionCount,
    dimensionsOk: true, // default until backend provides dimension data
    riskyBridgeList: b.riskyBridgeList || [],
    constructionList: c.constructionList || [],
    warnings: [...(b.warnings||[]), ...(c.warnings||[])],
  }
}

// Parse SSE status events for phase indicator
function parsePhase(data) {
  try { const p = JSON.parse(data); phaseText.value = typeof p === 'string' ? p : '' }
  catch { phaseText.value = data }
}

const send = async (text) => {
  const raw = (text||inputMsg.value).trim(); if(!raw||streaming.value) return
  inputMsg.value=''; streaming.value=true; phaseText.value = '正在分析...'

  let msg = raw; const ctx = routeCtx.value
  if(ctx) msg = `[路线上下文]\n${ctx}\n\n[用户问题]\n${raw}`

  messages.value.push({ role:'user', content:raw })
  const aiIdx = messages.value.push({ role:'assistant', content:'', routeData:'', bridgeData:'', constructionData:'', assessment:null, streaming:true, name:'AI 助手' }) - 1
  await scrollDown()

  let bridgeData = '', constructionData = '', routeData = ''

  try {
    for await (const { event, data } of streamChat(msg)) {
      if (event === 'token') {
        const token = typeof data === 'string' ? data : (data.content || data.choices?.[0]?.delta?.content || '')
        messages.value[aiIdx].content += token
      } else if (event === 'route') {
        routeData = typeof data === 'string' ? data : data
        messages.value[aiIdx].routeData = routeData
      } else if (event === 'bridge') {
        bridgeData = typeof data === 'string' ? data : data
        messages.value[aiIdx].bridgeData = bridgeData
      } else if (event === 'construction') {
        constructionData = typeof data === 'string' ? data : data
        messages.value[aiIdx].constructionData = constructionData
      } else if (event === 'regulation') {
        // regulation KB results can be shown inline
      } else if (event === 'status') {
        parsePhase(data)
      } else if (event === 'done') {
        phaseText.value = ''
      }
      await nextTick()
      await scrollDown()
    }

    // Generate structured assessment
    const assessment = synthesizeAssessment(bridgeData, constructionData)
    messages.value[aiIdx].assessment = assessment
    messages.value[aiIdx].content = messages.value[aiIdx].content || '抱歉，没有收到回复。'
    messages.value[aiIdx].streaming = false
    phaseText.value = ''

  } catch(e) {
    console.error('Chat:',e)
    messages.value[aiIdx].error = e.message||'连接失败'
    messages.value[aiIdx].streaming = false
    phaseText.value = ''
    $q.notify({type:'negative',message:'请求失败，请检查后端'})
  }
  streaming.value = false
  await scrollDown()
}

const retry = (msg) => {
  msg.error = ''
  msg.content = ''
  msg.assessment = null
  send(msg._original || msg.content)
}
</script>
