<template>
  <div class="transport-tracker q-pa-md">
    <div class="text-h6 q-mb-md">运输进度追踪</div>

    <q-card v-if="!order" class="bg-grey-2">
      <q-card-section class="text-center text-grey-7">
        <q-icon name="info" size="md" class="q-mb-sm" />
        <div>请选择一个运输单查看进度</div>
      </q-card-section>
    </q-card>

    <q-card v-else>
      <q-card-section>
        <!-- Order Header -->
        <div class="row items-center q-mb-lg">
          <div class="col">
            <div class="text-h6">{{ order.order_number }}</div>
            <div class="text-caption text-grey-7">
              创建时间: {{ formatDate(order.created_at) }}
            </div>
          </div>
          <div class="col-auto">
            <q-badge :color="statusColor(order.status)" text-color="white" class="q-pa-sm" style="font-size: 14px;">
              {{ statusLabel(order.status) }}
            </q-badge>
          </div>
        </div>

        <!-- Timeline Visualization -->
        <q-timeline color="primary">
          <q-timeline-entry
            v-for="(entry, index) in orderedTimeline"
            :key="entry.status"
            :icon="entry.is_active ? 'radio_button_checked' : (entry.is_completed ? 'check_circle' : 'radio_button_unchecked')"
            :color="entry.is_active ? 'primary' : (entry.is_completed ? 'green' : 'grey-5')"
            :class="{ 'active-stage': entry.is_active }"
          >
            <template v-slot:title>
              <div
                class="row items-center q-gutter-sm"
                style="cursor: pointer;"
                @click="toggleExpand(entry.status)"
              >
                <span :class="entry.is_active ? 'text-weight-bold text-primary' : (entry.is_completed ? 'text-green' : 'text-grey-5')">
                  {{ entry.label }}
                </span>
                <q-badge
                  v-if="entry.is_active"
                  color="primary"
                  text-color="white"
                  class="q-ml-sm"
                >
                  当前
                </q-badge>
                <q-badge
                  v-else-if="entry.is_completed"
                  color="green"
                  text-color="white"
                  class="q-ml-sm"
                >
                  已完成
                </q-badge>
                <q-icon
                  :name="expandedStage === entry.status ? 'expand_less' : 'expand_more'"
                  size="sm"
                  class="q-ml-auto"
                />
              </div>
            </template>

            <template v-slot:subtitle>
              <span v-if="entry.timestamp" class="text-caption text-grey-6">
                {{ formatDate(entry.timestamp) }}
              </span>
              <span v-else class="text-caption text-grey-5">
                等待中...
              </span>
            </template>

            <!-- Expanded Details -->
            <div v-if="expandedStage === entry.status" class="q-mt-sm q-pa-sm bg-grey-1 rounded-borders">
              <div v-if="entry.notes" class="text-body2 q-mb-xs">
                <span class="text-weight-medium">备注:</span> {{ entry.notes }}
              </div>
              <div v-if="entry.changed_by" class="text-caption text-grey-6">
                <span class="text-weight-medium">操作人:</span> {{ entry.changed_by }}
              </div>
              <div v-if="!entry.notes && !entry.changed_by && !entry.is_active" class="text-caption text-grey-5">
                暂无详情
              </div>
            </div>
          </q-timeline-entry>
        </q-timeline>

        <!-- Stage Progress Bar -->
        <div class="q-mt-lg q-pt-md" style="border-top: 1px solid #e0e0e0;">
          <div class="text-caption text-grey-7 q-mb-sm">整体进度</div>
          <div class="row items-center">
            <q-linear-progress
              :value="progressFraction"
              color="primary"
              class="col"
              style="height: 10px; border-radius: 5px;"
            />
            <span class="q-ml-sm text-caption text-weight-bold text-primary">
              {{ progressPercent }}%
            </span>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  order: {
    type: Object,
    default: null
  }
})

const expandedStage = ref(null)

// Ordered stages in the transport lifecycle
const STAGE_ORDER = [
  'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'FIELD_SURVEY',
  'APPROVED', 'PERMIT_ISSUED', 'IN_TRANSIT', 'COMPLETED'
]

const STAGE_LABELS = {
  DRAFT: '草稿',
  SUBMITTED: '申请提交',
  UNDER_REVIEW: '受理审核',
  FIELD_SURVEY: '现场勘验',
  APPROVED: '审批通过',
  REJECTED: '审批驳回',
  PERMIT_ISSUED: '已发证',
  IN_TRANSIT: '运输中',
  COMPLETED: '到达完成',
  CANCELLED: '已取消'
}

const STATUS_COLORS = {
  DRAFT: 'grey',
  SUBMITTED: 'blue',
  UNDER_REVIEW: 'orange',
  FIELD_SURVEY: 'purple',
  APPROVED: 'green',
  REJECTED: 'red',
  PERMIT_ISSUED: 'teal',
  IN_TRANSIT: 'primary',
  COMPLETED: 'green-8',
  CANCELLED: 'red-8'
}

function toggleExpand(status) {
  expandedStage.value = expandedStage.value === status ? null : status
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function statusLabel(status) {
  return STAGE_LABELS[status] || status
}

function statusColor(status) {
  return STATUS_COLORS[status] || 'grey'
}

const orderedTimeline = computed(() => {
  if (!props.order || !props.order.timeline) return []

  const timelineMap = {}
  if (props.order.timeline) {
    props.order.timeline.forEach(entry => {
      timelineMap[entry.status] = entry
    })
  }

  // Build ordered timeline using STAGE_ORDER
  const result = STAGE_ORDER.map(stage => {
    const entry = timelineMap[stage]
    if (entry) return entry
    return {
      status: stage,
      label: STAGE_LABELS[stage] || stage,
      timestamp: null,
      is_completed: false,
      is_active: false,
      notes: null,
      changed_by: null
    }
  })

  // Append CANCELLED/REJECTED if present
  if (props.order.status === 'CANCELLED' || props.order.status === 'REJECTED') {
    const terminalEntry = props.order.timeline.find(e => e.status === props.order.status)
    if (terminalEntry) {
      result.push(terminalEntry)
    }
  }

  return result
})

const completedCount = computed(() => {
  return orderedTimeline.value.filter(e => e.is_completed).length
})

const totalStages = computed(() => {
  return STAGE_ORDER.length
})

const progressFraction = computed(() => {
  if (totalStages.value === 0) return 0
  return Math.min(completedCount.value / totalStages.value, 1.0)
})

const progressPercent = computed(() => {
  return Math.round(progressFraction.value * 100)
})

// Reset expanded stage when order changes
watch(() => props.order, () => {
  expandedStage.value = null
})
</script>

<style scoped>
.transport-tracker {
  max-width: 100%;
}

.active-stage :deep(.q-timeline__title) {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.active-stage :deep(.q-timeline__dot) {
  box-shadow: 0 0 0 4px rgba(25, 118, 210, 0.3);
}
</style>
