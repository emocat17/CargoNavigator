<template>
  <div class="status-dashboard q-pa-md">
    <div class="text-h6 q-mb-md">运输追踪总览</div>

    <!-- Summary Cards -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-6 col-md-3">
        <q-card flat bordered class="bg-blue-1">
          <q-card-section>
            <div class="text-caption text-grey-7">总运输单</div>
            <div class="text-h4 text-blue-9">{{ stats.total_orders }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="bg-orange-1">
          <q-card-section>
            <div class="text-caption text-grey-7">待处理</div>
            <div class="text-h4 text-orange-9">{{ stats.active_orders }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="bg-teal-1">
          <q-card-section>
            <div class="text-caption text-grey-7">运输中</div>
            <div class="text-h4 text-teal-9">{{ stats.total_in_transit }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="bg-green-1">
          <q-card-section>
            <div class="text-caption text-grey-7">今日完成</div>
            <div class="text-h4 text-green-9">{{ stats.completed_today }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Quick Filter Bar -->
    <div class="row items-center q-mb-md q-gutter-sm">
      <q-btn-group spread>
        <q-btn
          v-for="filter in statusFilters"
          :key="filter.value"
          :label="filter.label"
          :color="activeFilter === filter.value ? 'primary' : 'grey-5'"
          :text-color="activeFilter === filter.value ? 'white' : 'black'"
          flat
          no-caps
          size="sm"
          @click="setFilter(filter.value)"
        />
      </q-btn-group>
      <q-space />
      <q-btn
        color="primary"
        icon="refresh"
        label="刷新"
        outline
        size="sm"
        @click="refreshData"
        :loading="loading"
      />
    </div>

    <!-- Orders Table -->
    <q-table
      :rows="filteredOrders"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :rows-per-page-options="[10, 20, 50]"
      flat
      bordered
      @row-click="onRowClick"
      :pagination="{ rowsPerPage: 20 }"
    >
      <template v-slot:body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="statusColor(props.value)" text-color="white">
            {{ statusLabel(props.value) }}
          </q-badge>
        </q-td>
      </template>

      <template v-slot:body-cell-order_number="props">
        <q-td :props="props">
          <span class="text-weight-medium text-primary" style="cursor: pointer;">
            {{ props.value }}
          </span>
        </q-td>
      </template>

      <template v-slot:body-cell-created_at="props">
        <q-td :props="props">
          {{ formatDate(props.value) }}
        </q-td>
      </template>

      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
          <q-btn
            flat
            round
            color="primary"
            icon="visibility"
            size="sm"
            @click.stop="$emit('view-order', props.row)"
          >
            <q-tooltip>查看详情</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <!-- Extra Stats -->
    <div v-if="stats.approval_rate !== null || stats.avg_processing_days !== null" class="row q-mt-md q-col-gutter-md">
      <div class="col-6" v-if="stats.approval_rate !== null">
        <q-card flat bordered class="bg-grey-1">
          <q-card-section>
            <div class="text-caption text-grey-7">审批通过率</div>
            <div class="text-h5 text-positive">{{ stats.approval_rate }}%</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6" v-if="stats.avg_processing_days !== null">
        <q-card flat bordered class="bg-grey-1">
          <q-card-section>
            <div class="text-caption text-grey-7">平均处理天数</div>
            <div class="text-h5 text-primary">{{ stats.avg_processing_days }} 天</div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['view-order'])

const API = import.meta.env.VITE_API_BASE || 'http://localhost:9876'
const loading = ref(false)
const orders = ref([])
const stats = ref({
  total_orders: 0,
  active_orders: 0,
  total_in_transit: 0,
  completed_today: 0,
  approval_rate: null,
  avg_processing_days: null,
  by_status: {}
})

const activeFilter = ref('ALL')

const statusFilters = [
  { label: '全部', value: 'ALL' },
  { label: '待提交', value: 'DRAFT' },
  { label: '审核中', value: 'UNDER_REVIEW' },
  { label: '勘验中', value: 'FIELD_SURVEY' },
  { label: '运输中', value: 'IN_TRANSIT' },
  { label: '已完成', value: 'COMPLETED' }
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

const columns = [
  { name: 'order_number', label: '运输单号', field: 'order_number', align: 'left', sortable: true },
  { name: 'status', label: '状态', field: 'status', align: 'center', sortable: true },
  { name: 'created_at', label: '创建时间', field: 'created_at', align: 'center', sortable: true },
  { name: 'updated_at', label: '更新时间', field: 'updated_at', align: 'center', sortable: true },
  { name: 'notes', label: '备注', field: 'notes', align: 'left' },
  { name: 'actions', label: '操作', field: 'actions', align: 'center', sortable: false }
]

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

function setFilter(status) {
  activeFilter.value = status
}

function onRowClick(evt, row) {
  emit('view-order', row)
}

const filteredOrders = computed(() => {
  if (activeFilter.value === 'ALL') return orders.value
  return orders.value.filter(o => o.status === activeFilter.value)
})

async function loadOrders() {
  try {
    const res = await axios.get(`${API}/api/v1/tracking/orders`, { params: { limit: 500, sort_desc: true } })
    if (res.data.code === 200) {
      orders.value = res.data.data.orders || []
    }
  } catch (e) {
    console.error('Failed to load orders:', e)
  }
}

async function loadStats() {
  try {
    const res = await axios.get(`${API}/api/v1/tracking/statistics`)
    if (res.data.code === 200) {
      stats.value = res.data.data
    }
  } catch (e) {
    console.error('Failed to load stats:', e)
  }
}

async function refreshData() {
  loading.value = true
  try {
    await Promise.all([loadOrders(), loadStats()])
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refreshData()
})

defineExpose({ refreshData })
</script>

<style scoped>
.status-dashboard {
  max-width: 100%;
}
</style>
