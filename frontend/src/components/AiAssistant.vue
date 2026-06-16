<template>
  <!-- ===== AI 浮球 ===== -->
  <div class="ai-float" v-if="!open">
    <q-btn round color="primary" icon="smart_toy" size="lg" @click="open = true" class="ai-btn" />
  </div>

  <!-- ===== AI 对话面板 ===== -->
  <div v-if="open" class="ai-panel">
    <div class="ai-panel-header">
      <q-icon name="smart_toy" size="sm" class="q-mr-sm" />
      <span class="text-weight-bold">AI 助手</span>
      <q-space />
      <q-btn dense flat round icon="close" size="sm" @click="open = false" />
    </div>

    <q-scroll-area ref="chatScroll" class="ai-messages">
      <div v-if="messages.length === 0" class="text-center text-grey-5 q-pa-md">
        <q-icon name="smart_toy" size="2rem" class="q-mb-sm" />
        <div class="text-caption">问我关于路线安全、施工信息、或运输规定的问题</div>
        <div class="q-mt-sm">
          <q-chip v-for="q in quickQuestions" :key="q" clickable size="sm" color="primary" text-color="white" @click="send(q)">{{ q }}</q-chip>
        </div>
      </div>

      <div v-for="(msg, i) in messages" :key="i" class="q-mb-sm">
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="row justify-end q-mb-xs">
          <div class="ai-msg-user">{{ msg.content }}</div>
        </div>
        <!-- AI 消息 -->
        <div v-else class="row items-start q-mb-xs">
          <div class="ai-msg-ai">
            <div v-if="msg.error" class="text-red text-caption">{{ msg.error }}
              <q-btn dense flat size="xs" label="重试" @click="retry(msg)" />
            </div>
            <div v-if="msg.content" style="white-space: pre-wrap;">{{ msg.content }}</div>

            <!-- 评估卡片 -->
            <div v-if="msg.assessment" class="q-mt-xs q-pa-xs bg-blue-1 rounded-borders">
              <div class="row items-center">
                <q-badge :color="riskBadgeColor(msg.assessment.riskLevel)" class="q-pa-xs">{{ msg.assessment.riskLevel }}</q-badge>
                <span class="text-caption q-ml-sm">{{ msg.assessment.summary }}</span>
                <q-space />
                <span class="text-caption text-grey-6">{{ msg.assessment.score }}/10</span>
              </div>
              <div class="row q-mt-xs text-caption">
                <span class="q-mr-sm">🌉 {{ msg.assessment.passableBridges || 0 }}/{{ msg.assessment.totalBridges || 0 }}</span>
                <span class="q-mr-sm">🚧 {{ msg.assessment.constructionCount || 0 }}处</span>
                <span>📐 {{ msg.assessment.dimensionsOk ? '通过' : '警告' }}</span>
              </div>
            </div>

            <q-spinner-dots v-if="msg.streaming" size="sm" color="primary" />
          </div>
        </div>
      </div>
    </q-scroll-area>

    <div class="ai-input-row">
      <q-input dense outlined v-model="inputMsg" placeholder="输入问题..." @keyup.enter="send()" :disable="streaming">
        <template v-slot:after>
          <q-btn round dense flat icon="send" color="primary" @click="send()" :disable="!inputMsg.trim() || streaming" />
        </template>
      </q-input>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const props = defineProps({
  routes: { type: Array, default: () => [] },
  selectedRouteIndex: { type: Number, default: 0 },
  vehicle: { type: Object, default: null },
})
const API = import.meta.env.VITE_API_BASE || 'http://localhost:19876'

const open = ref(false)
const inputMsg = ref('')
const streaming = ref(false)
const messages = ref([])
const chatScroll = ref(null)

const currentRoute = computed(() => props.routes?.[props.selectedRouteIndex] || null)

const quickQuestions = computed(() => currentRoute.value
  ? ['走这条路安全吗？有什么风险？', '沿途有哪些施工路段？', '这条路需要办理什么许可？']
  : ['福建高速最近有什么施工？', '从三明到平潭怎么走？', '大件运输有哪些规定？'])

const routeCtx = computed(() => {
  const r = currentRoute.value; if (!r) return ''
  return [`当前路线: ${r._origin || '?'} → ${r._destination || '?'}`, `距离: ${(r.distance / 1000).toFixed(1)}km`, `耗时: ${fmtD(r.duration)}`, `路径: ${r.route_description || ''}`].join('\n')
})

async function send(text) {
  const raw = (text || inputMsg.value).trim(); if (!raw || streaming.value) return
  inputMsg.value = ''; streaming.value = true

  let msg = raw; const ctx = routeCtx.value
  if (ctx) msg = `[路线上下文]\n${ctx}\n\n[用户问题]\n${raw}`

  messages.value.push({ role: 'user', content: raw })
  const aiIdx = messages.value.push({ role: 'assistant', content: '', assessment: null, streaming: true }) - 1
  await scrollDown()

  let bridgeData = '', constructionData = ''

  try {
    const resp = await fetch(`${API}/api/v1/agent/chat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader(); const decoder = new TextDecoder(); let buffer = ''
    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n'); buffer = events.pop()
      for (const evt of events) {
        if (!evt.trim()) continue
        const lines = evt.split('\n'); let et = '', d = ''
        for (const l of lines) { if (l.startsWith('event: ')) et = l.slice(7).trim(); else if (l.startsWith('data: ')) d = l.slice(6) }
        if (!et) continue
        let parsed; try { parsed = JSON.parse(d) } catch { parsed = d }
        if (et === 'token') { const t = typeof parsed === 'string' ? parsed : (parsed.content || parsed.choices?.[0]?.delta?.content || ''); messages.value[aiIdx].content += t }
        else if (et === 'bridge') bridgeData = typeof parsed === 'string' ? parsed : parsed
        else if (et === 'construction') constructionData = typeof parsed === 'string' ? parsed : parsed
      }
      await nextTick(); await scrollDown()
    }
    messages.value[aiIdx].assessment = synthesize(bridgeData, constructionData)
    messages.value[aiIdx].streaming = false
  } catch (e) {
    messages.value[aiIdx].error = e.message || '连接失败'; messages.value[aiIdx].streaming = false
  }
  streaming.value = false
}

function retry(msg) { msg.error = ''; msg.content = ''; msg.assessment = null; send(msg._original || msg.content) }

function synthesize(bridgeText, constructionText) {
  const risky = (bridgeText?.match(/存在风险:\s*(\d+)/) || [])[1]
  const total = (bridgeText?.match(/桥梁总数:\s*(\d+)/) || [])[1]
  const maxRatio = (bridgeText?.match(/最大效应比值:\s*([\d.]+)/) || [])[1]
  const safe = (bridgeText?.match(/安全通行:\s*(\d+)/) || [])[1]
  const constCount = (constructionText?.match(/(\d+)\s*条与路线段落精确重叠/) || [])[1] || (constructionText?.match(/(\d+)\s*处/) || [])[1]

  const riskyB = parseInt(risky) || 0; const totalB = parseInt(total) || 0
  const maxR = parseFloat(maxRatio) || 0; const constC = parseInt(constCount) || 0
  let riskLevel = '低', score = 10
  if (riskyB > 2 || maxR >= 2) { riskLevel = '极高'; score = 2 }
  else if (riskyB > 0 || maxR >= 1) { riskLevel = '高'; score = 4 }
  else if (maxR >= 0.8 || constC > 3) { riskLevel = '中'; score = 7 }

  const parts = []; if (riskyB > 0) parts.push(`${riskyB}座桥梁存在风险`)
  else if (totalB > 0) parts.push(`${totalB}座桥梁可通行`)
  if (constC > 0) parts.push(`${constC}处施工与路线重叠`)
  return { riskLevel, score, summary: parts.join('，') || '路线已评估', totalBridges: totalB, passableBridges: parseInt(safe) || 0, riskyBridges: riskyB, maxRatio: maxR, constructionCount: constC, dimensionsOk: true }
}

function riskBadgeColor(level) { return ({ '低': 'green', '中': 'orange', '高': 'red', '极高': 'deep-orange' })[level] || 'grey' }
function fmtD(s) { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h > 0 ? `${h}h${m}m` : `${m}min` }
async function scrollDown() { await nextTick(); const el = chatScroll.value?.$el || chatScroll.value; if (el) el.scrollTop = el.scrollHeight }
</script>

<style scoped>
.ai-float { position: fixed; bottom: 56px; right: 24px; z-index: 999; }
.ai-btn { animation: breathe 2s ease-in-out infinite; box-shadow: 0 4px 16px rgba(37,99,235,0.4); }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }

.ai-panel {
  position: fixed; bottom: 56px; right: 24px;
  width: 400px; height: 520px;
  background: #fff; border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.25);
  display: flex; flex-direction: column; z-index: 998;
}
.ai-panel-header { padding: 10px 14px; display: flex; align-items: center; background: #f8fafc; border-radius: 16px 16px 0 0; border-bottom: 1px solid #e2e8f0; }
.ai-messages { flex: 1; padding: 10px; overflow-y: auto; }
.ai-msg-user { background: #2563eb; color: #fff; padding: 6px 10px; border-radius: 10px 10px 0 10px; max-width: 85%; font-size: 13px; }
.ai-msg-ai { background: #f1f5f9; padding: 6px 10px; border-radius: 10px 10px 10px 0; font-size: 13px; max-width: 85%; }
.ai-input-row { padding: 8px; border-top: 1px solid #e2e8f0; }
</style>
