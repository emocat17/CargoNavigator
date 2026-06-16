<template>
  <div class="axle-configurator">
    <!-- Controls bar -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <q-btn
        round
        color="primary"
        icon="add"
        size="sm"
        :disable="axleCount >= maxAxles"
        @click="addAxle"
      >
        <q-tooltip>增加一轴</q-tooltip>
      </q-btn>
      <q-btn
        round
        color="negative"
        icon="remove"
        size="sm"
        :disable="axleCount <= minAxles"
        @click="removeAxle"
      >
        <q-tooltip>减少一轴</q-tooltip>
      </q-btn>
      <q-separator vertical />
      <div class="text-caption text-grey-7">
        轴数: <strong>{{ axleCount }}</strong>
      </div>
      <q-space />
      <div class="text-caption text-grey-7">
        总轴距: <strong>{{ totalSpacing.toFixed(2) }}</strong> m
      </div>
    </div>

    <!-- SVG Diagram -->
    <div class="diagram-container q-mb-md" ref="diagramRef">
      <svg
        :viewBox="`0 -10 ${svgWidth} 160`"
        xmlns="http://www.w3.org/2000/svg"
        class="axle-diagram"
        preserveAspectRatio="xMidYMid meet"
      >
        <!-- Vehicle body outline (top-down view) -->
        <rect
          x="10"
          y="10"
          :width="totalLengthPx"
          height="60"
          rx="4"
          fill="#e3f2fd"
          stroke="#1976d2"
          stroke-width="1.5"
        />

        <!-- Tractor cab -->
        <rect
          x="10"
          y="10"
          :width="tractorLengthPx"
          height="60"
          rx="4"
          fill="#bbdefb"
          stroke="#1976d2"
          stroke-width="1.5"
        />

        <!-- Tractor label -->
        <text
          :x="10 + tractorLengthPx / 2"
          y="53"
          text-anchor="middle"
          font-size="10"
          fill="#1565c0"
          font-weight="bold"
        >牵引车</text>

        <!-- Trailer label -->
        <text
          :x="10 + tractorLengthPx + trailerLengthPx / 2"
          y="53"
          text-anchor="middle"
          font-size="10"
          fill="#1565c0"
          font-weight="bold"
        >挂车</text>

        <!-- Divider line between tractor and trailer -->
        <line
          :x1="10 + tractorLengthPx"
          y1="10"
          :x2="10 + tractorLengthPx"
          y2="70"
          stroke="#1976d2"
          stroke-width="1"
          stroke-dasharray="4,4"
        />

        <!-- Axle lines -->
        <g v-for="(pos, idx) in axlePositionsPx" :key="idx">
          <!-- Axle bar -->
          <line
            :x1="pos"
            y1="5"
            :x2="pos"
            y2="75"
            :stroke="idx === 0 ? '#e65100' : '#1976d2'"
            stroke-width="2.5"
          />
          <!-- Axle wheels (small rectangles at ends) -->
          <rect :x="pos - 4" y="2" width="8" height="8" rx="2" fill="#333" />
          <rect :x="pos - 4" y="70" width="8" height="8" rx="2" fill="#333" />
          <!-- Axle label -->
          <text
            :x="pos"
            y="92"
            text-anchor="middle"
            font-size="9"
            fill="#555"
          >轴{{ idx + 1 }}</text>
          <!-- Weight label -->
          <text
            :x="pos"
            y="105"
            text-anchor="middle"
            font-size="8"
            fill="#e65100"
          >{{ axleLoads[idx] || 0 }}t</text>
        </g>

        <!-- Spacing arrows and labels -->
        <g v-for="(sp, idx) in spacings" :key="'sp' + idx">
          <!-- Arrow line -->
          <line
            :x1="axlePositionsPx[idx]"
            y1="120"
            :x2="axlePositionsPx[idx + 1]"
            y2="120"
            stroke="#43a047"
            stroke-width="1.5"
          />
          <!-- Arrow heads -->
          <polygon
            :points="arrowHead(idx, 'left')"
            fill="#43a047"
          />
          <polygon
            :points="arrowHead(idx, 'right')"
            fill="#43a047"
          />
          <!-- Spacing value -->
          <text
            :x="(axlePositionsPx[idx] + axlePositionsPx[idx + 1]) / 2"
            y="135"
            text-anchor="middle"
            font-size="9"
            fill="#2e7d32"
            font-weight="bold"
          >{{ spacings[idx].toFixed(2) }}</text>
          <!-- Unit -->
          <text
            :x="(axlePositionsPx[idx] + axlePositionsPx[idx + 1]) / 2"
            y="148"
            text-anchor="middle"
            font-size="8"
            fill="#777"
          >m</text>
        </g>

        <!-- Front label -->
        <text x="10" y="155" text-anchor="start" font-size="8" fill="#999">车头</text>
        <!-- Rear label -->
        <text :x="10 + totalLengthPx" y="155" text-anchor="end" font-size="8" fill="#999">车尾</text>
      </svg>
    </div>

    <!-- Spacing inputs -->
    <div class="text-subtitle2 q-mb-sm">轴距配置 (米)</div>
    <div class="row q-col-gutter-sm">
      <div
        v-for="(sp, idx) in spacings"
        :key="'inp' + idx"
        class="col-6 col-md-4 col-lg-3"
      >
        <q-input
          filled
          dense
          type="number"
          :model-value="sp"
          @update:model-value="val => updateSpacing(idx, parseFloat(val) || 0)"
          :label="`轴 ${idx + 1} → 轴 ${idx + 2}`"
          suffix="m"
          step="0.01"
          min="0.5"
          :rules="[val => val > 0 || '轴距需大于0']"
        />
      </div>
    </div>

    <!-- Axle load distribution -->
    <div class="text-subtitle2 q-mb-sm q-mt-md">轴重分配 (吨)</div>
    <div class="row items-center q-gutter-sm q-mb-sm">
      <q-btn
        flat
        dense
        color="primary"
        icon="balance"
        label="均匀分配"
        @click="distributeEvenly"
        size="sm"
      />
      <div class="text-caption text-grey-7" v-if="totalWeight > 0">
        总重: {{ totalWeight }}t | 已分配: {{ allocatedWeight.toFixed(1) }}t
        <span v-if="Math.abs(totalWeight - allocatedWeight) > 0.05" class="text-negative">
          (差 {{ (totalWeight - allocatedWeight).toFixed(1) }}t)
        </span>
      </div>
    </div>
    <div class="row q-col-gutter-sm">
      <div
        v-for="(load, idx) in axleLoads"
        :key="'load' + idx"
        class="col-4 col-md-3 col-lg-2"
      >
        <q-input
          filled
          dense
          type="number"
          v-model.number="axleLoads[idx]"
          :label="`轴 ${idx + 1} 重量`"
          suffix="t"
          step="0.1"
          min="0"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      axleCount: 5,
      spacings: [3.2, 1.4, 7.0, 1.45],
      axleLoads: [10, 10, 10, 17.98, 17.98],
      totalWeight: 150,
      tractorLength: 8,
      trailerLength: 16
    })
  }
})

const emit = defineEmits(['update:modelValue'])

const minAxles = 2
const maxAxles = 20

const axleCount = ref(props.modelValue.axleCount || 5)
const spacings = ref([...(props.modelValue.spacings || [3.2, 1.4, 7.0, 1.45])])
const axleLoads = ref([...(props.modelValue.axleLoads || [10, 10, 10, 17.98, 17.98])])
const tractorLength = ref(props.modelValue.tractorLength || 8)
const trailerLength = ref(props.modelValue.trailerLength || 16)
const totalWeight = ref(props.modelValue.totalWeight || 150)

// Sync from parent when modelValue changes
watch(() => props.modelValue, (val) => {
  if (!val) return
  axleCount.value = val.axleCount || axleCount.value
  if (val.spacings) spacings.value = [...val.spacings]
  if (val.axleLoads) axleLoads.value = [...val.axleLoads]
  tractorLength.value = val.tractorLength || tractorLength.value
  trailerLength.value = val.trailerLength || trailerLength.value
  totalWeight.value = val.totalWeight || totalWeight.value
}, { deep: true })

const totalLength = computed(() => tractorLength.value + trailerLength.value)

const svgWidth = computed(() => {
  const len = totalLength.value
  // Scale: roughly 10px per meter, minimum 400px viewbox width
  return Math.max(len * 30, 400)
})

const scaleMtoPx = computed(() => svgWidth.value / totalLength.value)

const tractorLengthPx = computed(() => tractorLength.value * scaleMtoPx.value)
const trailerLengthPx = computed(() => trailerLength.value * scaleMtoPx.value)
const totalLengthPx = computed(() => totalLength.value * scaleMtoPx.value)

// Axle positions calculated from spacings.
// First axle is at the front of the vehicle + a small offset
const axlePositionsPx = computed(() => {
  const positions = []
  // First axle at front of trailer section
  let cumulative = 10 + tractorLengthPx.value // first axle at tractor-trailer boundary
  positions.push(cumulative)
  // For tractors, first axle might be under the tractor; but for simplicity,
  // we place first axle at the tractor-trailer joint and subsequent axles based on spacings.

  // Actually, let's place axles from the front of the vehicle based on spacings
  // The spacings represent distances between consecutive axles
  // Axle 0 is at the distance_from_front which is the tractor length roughly
  // Wait, let me reconsider. The first axle of the trailer is typically behind the tractor.
  // For our diagram, let's place the first axle at the tractor length point, and then
  // each subsequent axle's position is determined by adding the spacing.

  return positions
})

// Recalculate: Actually let's place axles starting from the tractor-trailer junction
// and going backward. Spacings[i] is the distance from axle[i] to axle[i+1]
const axlePositionsPxCalc = computed(() => {
  const positions = []
  let pos = 10 + tractorLengthPx.value
  for (let i = 0; i < axleCount.value; i++) {
    if (i === 0) {
      // First axle: could be on tractor or start of trailer
      // Let's place it slightly into the trailer area
      positions.push(pos)
    } else {
      const sp = spacings.value[i - 1] || 1.4
      pos += sp * scaleMtoPx.value
      positions.push(pos)
    }
  }
  return positions
})

const totalSpacing = computed(() => {
  return spacings.value.reduce((a, b) => a + b, 0)
})

const allocatedWeight = computed(() => {
  return axleLoads.value.reduce((a, b) => a + (b || 0), 0)
})

const svgWidthComputed = computed(() => {
  const lastAxlePos = axlePositionsPxCalc.value[axlePositionsPxCalc.value.length - 1] || 400
  return Math.max(lastAxlePos + 60, 400)
})

// Override svgWidth with computed based on actual axle positions
const svgWidthActual = computed(() => {
  const lastPos = axlePositionsPxCalc.value[axlePositionsPxCalc.value.length - 1] || 0
  return Math.max(lastPos + 60, 500)
})

const arrowHead = (idx, side) => {
  const left = axlePositionsPxCalc.value[idx]
  const right = axlePositionsPxCalc.value[idx + 1]
  const y = 120
  const size = 4
  if (side === 'left') {
    return `${left + 2},${y - size} ${left + 2},${y + size} ${left + 2 + size},${y}`
  } else {
    return `${right - 2},${y - size} ${right - 2},${y + size} ${right - 2 - size},${y}`
  }
}

const addAxle = () => {
  if (axleCount.value >= maxAxles) return
  axleCount.value++
  const avgSpacing = spacings.value.length > 0
    ? spacings.value.reduce((a, b) => a + b, 0) / spacings.value.length
    : 1.4
  spacings.value.push(avgSpacing)
  const avgLoad = totalWeight.value > 0 ? totalWeight.value / axleCount.value : 10
  axleLoads.value.push(Math.round(avgLoad * 100) / 100)
  emitUpdate()
}

const removeAxle = () => {
  if (axleCount.value <= minAxles) return
  axleCount.value--
  spacings.value.pop()
  axleLoads.value.pop()
  emitUpdate()
}

const updateSpacing = (index, value) => {
  if (value <= 0) return
  spacings.value[index] = value
  // Update into a new array to trigger reactivity
  spacings.value = [...spacings.value]
  emitUpdate()
}

const distributeEvenly = () => {
  if (axleCount.value === 0 || totalWeight.value <= 0) return
  const evenLoad = Math.round((totalWeight.value / axleCount.value) * 100) / 100
  for (let i = 0; i < axleCount.value; i++) {
    axleLoads.value[i] = evenLoad
  }
  // Adjust last axle to account for rounding
  const sum = axleLoads.value.reduce((a, b) => a + b, 0)
  axleLoads.value[axleCount.value - 1] += Math.round((totalWeight.value - sum) * 100) / 100
  axleLoads.value = [...axleLoads.value]
  emitUpdate()
}

const emitUpdate = () => {
  emit('update:modelValue', {
    axleCount: axleCount.value,
    spacings: [...spacings.value],
    axleLoads: [...axleLoads.value],
    totalWeight: totalWeight.value,
    tractorLength: tractorLength.value,
    trailerLength: trailerLength.value
  })
}

const reset = (config) => {
  axleCount.value = config.axleCount || 5
  spacings.value = [...(config.spacings || [3.2, 1.4, 7.0, 1.45])]
  axleLoads.value = [...(config.axleLoads || [10, 10, 10, 17.98, 17.98])]
  totalWeight.value = config.totalWeight || 150
  tractorLength.value = config.tractorLength || 8
  trailerLength.value = config.trailerLength || 16
}

const validate = () => {
  const errors = []
  if (spacings.value.some(s => s <= 0)) errors.push('所有轴距必须大于0')
  if (spacings.value.length !== axleCount.value - 1) errors.push(`轴距数量(${spacings.value.length})应为轴数-1(${axleCount.value - 1})`)
  if (axleLoads.value.length !== axleCount.value) errors.push(`轴重数量(${axleLoads.value.length})与轴数(${axleCount.value})不一致`)
  return {
    valid: errors.length === 0,
    errors
  }
}

defineExpose({ reset, validate, emitUpdate })
</script>

<style scoped>
.axle-configurator {
  width: 100%;
}

.diagram-container {
  width: 100%;
  overflow-x: auto;
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px;
}

.axle-diagram {
  width: 100%;
  min-width: 400px;
  height: auto;
  display: block;
}
</style>
