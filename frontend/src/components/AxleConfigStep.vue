<template>
  <div class="step-content">
    <!-- Weight Configuration -->
    <div class="text-h5 q-mb-sm">重量与轴数配置</div>
    <div class="text-body1 text-grey-7 q-mb-md">
      填写车货总重和轴数，系统将帮助您分配轴重
    </div>

    <div class="row q-col-gutter-sm">
      <div class="col-12 col-md-6">
        <q-input
          filled
          v-model.number="modelValue.total_weight"
          type="number"
          label="车货总质量"
          suffix="吨"
          step="1"
          min="1"
          :rules="[val => val > 0 || '必填']"
          class="q-mb-md"
        >
          <template v-slot:prepend>
            <q-icon name="scale" />
          </template>
        </q-input>
      </div>
      <div class="col-12 col-md-6">
        <q-input
          filled
          v-model.number="modelValue.axle_count"
          type="number"
          label="总轴数"
          step="1"
          min="2"
          max="20"
          :rules="[val => val >= 2 || '至少2轴', val => val <= 20 || '最多20轴']"
          class="q-mb-md"
        >
          <template v-slot:prepend>
            <q-icon name="settings" />
          </template>
        </q-input>
      </div>
    </div>

    <!-- Quick weight distribution bar -->
    <div v-if="modelValue.total_weight > 0 && modelValue.axle_count > 0" class="q-mb-md">
      <div class="text-subtitle2 q-mb-xs">轴重分布预览</div>
      <div class="weight-bar-container">
        <div
          v-for="i in modelValue.axle_count"
          :key="i"
          class="weight-bar-segment"
          :style="{ width: (100 / modelValue.axle_count) + '%' }"
        >
          <div class="weight-bar-fill" />
          <div class="weight-bar-label">轴{{ i }}</div>
          <div class="weight-bar-value">{{ (modelValue.total_weight / modelValue.axle_count).toFixed(1) }}t</div>
        </div>
      </div>
      <div class="text-caption text-grey-6 q-mt-xs">
        均匀分配: 每轴 {{ (modelValue.total_weight / modelValue.axle_count).toFixed(1) }} 吨 (可在下一步调整)
      </div>
    </div>

    <!-- Axle Load Quick Entry -->
    <div v-if="modelValue.axle_count >= 2" class="q-mt-lg">
      <div class="text-subtitle2 q-mb-sm">轴重快速设置 (吨)</div>
      <div class="row q-col-gutter-sm">
        <div
          v-for="i in Math.min(modelValue.axle_count, 10)"
          :key="'quick' + i"
          class="col-4 col-md-2"
        >
          <q-input
            filled
            dense
            type="number"
            v-model.number="axleLoadsLocal[i - 1]"
            :label="'轴' + i"
            suffix="t"
            step="0.1"
            min="0"
          />
        </div>
      </div>
    </div>

    <q-separator class="q-my-xl" />

    <!-- Axle Spacing Configuration -->
    <div class="text-h5 q-mb-sm">轴距配置</div>
    <div class="text-body1 text-grey-7 q-mb-md">
      配置各轴之间的间距。图中绿色箭头标出轴距，可点击数值修改。
    </div>

    <AxleConfigurator
      ref="axleConfigRef"
      v-model="axleConfig"
    />

    <q-banner rounded class="bg-grey-3 q-mt-lg">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      轴距 = 相邻两轴中心点之间的距离。第一轴通常位于牵引车驱动轴位置。液压悬挂挂车的轴距一般较小(1.3-1.5m)，低平板半挂车轴距较大(>3m)。
    </q-banner>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import AxleConfigurator from './AxleConfigurator.vue'

const props = defineProps({
  modelValue: { type: Object, required: true }
})

const emit = defineEmits(['update:modelValue'])

const axleConfigRef = ref(null)

// Local axle loads for quick entry
const axleLoadsLocal = ref([])

// Watch axle_count to resize axleLoadsLocal
watch(() => props.modelValue.axle_count, (count) => {
  if (!count) {
    axleLoadsLocal.value = []
    return
  }
  const newLoads = []
  const evenLoad = props.modelValue.total_weight ? parseFloat((props.modelValue.total_weight / count).toFixed(2)) : 0
  for (let i = 0; i < count; i++) {
    newLoads.push(axleLoadsLocal.value[i] || evenLoad)
  }
  axleLoadsLocal.value = newLoads
})

// Watch total_weight to auto-distribute
watch(() => props.modelValue.total_weight, (weight) => {
  if (props.modelValue.axle_count && weight) {
    const evenLoad = parseFloat((weight / props.modelValue.axle_count).toFixed(2))
    for (let i = 0; i < axleLoadsLocal.value.length; i++) {
      if (!axleLoadsLocal.value[i]) {
        axleLoadsLocal.value[i] = evenLoad
      }
    }
  }
})

// Axle config for the AxleConfigurator component
const axleConfig = computed({
  get: () => ({
    axleCount: props.modelValue.axle_count || 5,
    spacings: props.modelValue.axle_spacings.length > 0 ? [...props.modelValue.axle_spacings] : defaultSpacings(),
    axleLoads: props.modelValue.axle_loads.length > 0 ? [...props.modelValue.axle_loads] : defaultLoads(),
    totalWeight: props.modelValue.total_weight || 150,
    tractorLength: props.modelValue.tractor_length || 8,
    trailerLength: props.modelValue.trailer_length || 16
  }),
  set: (val) => {
    if (val.axleCount != null) props.modelValue.axle_count = val.axleCount
    if (val.spacings) props.modelValue.axle_spacings = [...val.spacings]
    if (val.axleLoads) props.modelValue.axle_loads = [...val.axleLoads]
    if (val.totalWeight != null) props.modelValue.total_weight = val.totalWeight
    if (val.tractorLength != null) props.modelValue.tractor_length = val.tractorLength
    if (val.trailerLength != null) props.modelValue.trailer_length = val.trailerLength
  }
})

function defaultSpacings() {
  const count = props.modelValue.axle_count || 5
  if (count <= 2) return [1.4]
  const spacings = []
  for (let i = 0; i < count - 1; i++) {
    spacings.push(i === 0 ? 3.2 : i < 3 ? 1.45 : 1.4)
  }
  return spacings
}

function defaultLoads() {
  const count = props.modelValue.axle_count || 5
  const total = props.modelValue.total_weight || 150
  const loads = []
  const evenLoad = parseFloat((total / count).toFixed(2))
  for (let i = 0; i < count; i++) {
    loads.push(evenLoad)
  }
  // Adjust last to account for rounding
  const sum = loads.reduce((a, b) => a + b, 0)
  if (loads.length > 0) {
    loads[loads.length - 1] += parseFloat((total - sum).toFixed(2))
  }
  return loads
}

// Expose validation for parent
function validate() {
  if (!props.modelValue.total_weight || props.modelValue.total_weight <= 0) {
    return { valid: false, errors: ['请填写车货总质量'] }
  }
  if (!props.modelValue.axle_count || props.modelValue.axle_count < 2) {
    return { valid: false, errors: ['轴数至少为2'] }
  }
  if (axleConfigRef.value) {
    const result = axleConfigRef.value.validate()
    if (!result.valid) {
      return result
    }
  }
  // Sync axle loads from quick entry if not set via configurator
  if (props.modelValue.axle_loads.length === 0) {
    props.modelValue.axle_loads = [...axleLoadsLocal.value]
  }
  return { valid: true, errors: [] }
}

// Sync data before entering axle configurator view
function syncToConfigurator() {
  if (props.modelValue.axle_spacings.length === 0) {
    props.modelValue.axle_spacings = defaultSpacings()
  }
  if (props.modelValue.axle_loads.length === 0) {
    props.modelValue.axle_loads = [...axleLoadsLocal.value]
  }
}

defineExpose({ validate, syncToConfigurator, axleLoadsLocal })
</script>

<style scoped>
.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.weight-bar-container {
  display: flex;
  height: 60px;
  background: #f5f5f5;
  border-radius: 6px;
  overflow: hidden;
  gap: 2px;
}

.weight-bar-segment {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.weight-bar-fill {
  width: 100%;
  height: 100%;
  background: linear-gradient(to top, #1976d2, #42a5f5);
  opacity: 0.7;
  border-radius: 2px 2px 0 0;
  min-height: 8px;
}

.weight-bar-label {
  position: absolute;
  bottom: 2px;
  font-size: 10px;
  color: white;
  font-weight: bold;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

.weight-bar-value {
  position: absolute;
  top: 6px;
  font-size: 10px;
  color: #1565c0;
  font-weight: bold;
}
</style>
