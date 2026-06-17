<template>
  <div class="step-content">
    <!-- Cargo Information -->
    <div class="text-h5 q-mb-sm">货物信息</div>
    <div class="text-body1 text-grey-7 q-mb-md">
      填写运输货物的详细信息
    </div>

    <div class="row q-col-gutter-sm">
      <div class="col-12 col-md-6">
        <q-input
          filled
          v-model="modelValue.cargo_name"
          label="货物名称"
          :rules="[val => !!val || '必填']"
        >
          <template v-slot:prepend>
            <q-icon name="inventory_2" />
          </template>
        </q-input>
      </div>
      <div class="col-12 col-md-6">
        <q-input
          filled
          v-model.number="modelValue.cargo_weight"
          type="number"
          label="货物质量"
          suffix="吨"
          step="1"
          min="0"
          :rules="[val => val >= 0 || '不能为负']"
        />
      </div>
      <div class="col-4">
        <q-input
          filled
          v-model.number="modelValue.cargo_length"
          type="number"
          label="货物长度"
          suffix="m"
          step="0.1"
          min="0"
        />
      </div>
      <div class="col-4">
        <q-input
          filled
          v-model.number="modelValue.cargo_width"
          type="number"
          label="货物宽度"
          suffix="m"
          step="0.1"
          min="0"
        />
      </div>
      <div class="col-4">
        <q-input
          filled
          v-model.number="modelValue.cargo_height"
          type="number"
          label="货物高度"
          suffix="m"
          step="0.1"
          min="0"
        />
      </div>
    </div>

    <!-- Cargo dimension helper -->
    <q-banner rounded class="bg-amber-1 q-mt-md" v-if="hasCargoSizeIssue">
      <template v-slot:avatar>
        <q-icon name="warning" color="orange" />
      </template>
      <span v-if="modelValue.cargo_length > modelValue.length">
        货物长度({{ modelValue.cargo_length }}m)超过车货总长({{ modelValue.length }}m)，请检查
      </span>
      <span v-else-if="modelValue.cargo_width > modelValue.width">
        货物宽度({{ modelValue.cargo_width }}m)超过车货总宽({{ modelValue.width }}m)，请检查
      </span>
      <span v-else-if="modelValue.cargo_height > modelValue.height">
        货物高度({{ modelValue.cargo_height }}m)超过车货总高({{ modelValue.height }}m)，请检查
      </span>
    </q-banner>

    <q-separator class="q-my-xl" />

    <!-- Summary & Confirmation -->
    <div class="text-h5 q-mb-sm">配置摘要</div>
    <div class="text-body1 text-grey-7 q-mb-md">
      请确认以下车辆配置信息，确认无误后点击"完成配置"
    </div>

    <div class="row q-col-gutter-md">
      <!-- Vehicle type -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-primary">挂车类型</div>
            <div class="text-body1 q-mt-sm">{{ selectedTypeName }}</div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Dimensions -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-primary">外廓尺寸</div>
            <div class="row q-mt-sm">
              <div class="col-4 text-center">
                <div class="text-caption text-grey-7">总长</div>
                <div class="text-h6">{{ modelValue.length || '-' }}<span class="text-caption">m</span></div>
              </div>
              <div class="col-4 text-center">
                <div class="text-caption text-grey-7">总宽</div>
                <div class="text-h6">{{ modelValue.width || '-' }}<span class="text-caption">m</span></div>
              </div>
              <div class="col-4 text-center">
                <div class="text-caption text-grey-7">总高</div>
                <div class="text-h6">{{ modelValue.height || '-' }}<span class="text-caption">m</span></div>
              </div>
            </div>
            <q-separator class="q-my-sm" />
            <div class="row text-center">
              <div class="col-6">
                <div class="text-caption text-grey-7">牵引车长</div>
                <div class="text-body1">{{ modelValue.tractor_length || '-' }}m</div>
              </div>
              <div class="col-6">
                <div class="text-caption text-grey-7">挂车长</div>
                <div class="text-body1">{{ modelValue.trailer_length || '-' }}m</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Weight -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-primary">重量配置</div>
            <div class="row q-mt-sm">
              <div class="col-6 text-center">
                <div class="text-caption text-grey-7">车货总重</div>
                <div class="text-h6">{{ modelValue.total_weight || '-' }}<span class="text-caption">t</span></div>
              </div>
              <div class="col-6 text-center">
                <div class="text-caption text-grey-7">总轴数</div>
                <div class="text-h6">{{ modelValue.axle_count || '-' }}<span class="text-caption">轴</span></div>
              </div>
            </div>
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey-7">轴重分布</div>
            <div class="text-body2">{{ axleLoadsDisplay }}</div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Axle Spacing -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-primary">轴距配置</div>
            <div class="text-caption text-grey-7 q-mt-sm">轴距分布 (共{{ modelValue.axle_spacings.length }}段)</div>
            <div class="text-body2">{{ axleSpacingsDisplay }}</div>
            <div class="text-caption text-grey-7 q-mt-sm">
              总轴距: {{ totalAxleSpacing.toFixed(2) }}m
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Cargo -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-primary">货物信息</div>
            <div class="text-body1 q-mt-sm">{{ modelValue.cargo_name || '-' }}</div>
            <div class="row q-mt-xs">
              <div class="col-4 text-center">
                <div class="text-caption text-grey-7">长</div>
                <div class="text-body2">{{ modelValue.cargo_length || '-' }}m</div>
              </div>
              <div class="col-4 text-center">
                <div class="text-caption text-grey-7">宽</div>
                <div class="text-body2">{{ modelValue.cargo_width || '-' }}m</div>
              </div>
              <div class="col-4 text-center">
                <div class="text-caption text-grey-7">高</div>
                <div class="text-body2">{{ modelValue.cargo_height || '-' }}m</div>
              </div>
            </div>
            <div class="text-body2 q-mt-sm">货物重量: {{ modelValue.cargo_weight || '-' }}t</div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true }
})

const emit = defineEmits(['update:modelValue', 'save'])

// Vehicle type names (duplicated from VehicleFormStep for display)
const vehicleTypeNames = {
  lowbed: '低平板半挂车',
  hydraulic: '多轴液压悬挂挂车',
  combo: '特殊组合液压悬挂挂车'
}

const selectedTypeName = computed(() => {
  return vehicleTypeNames[props.modelValue.trailer_type] || ''
})

// Cargo size check
const hasCargoSizeIssue = computed(() => {
  return (
    (props.modelValue.cargo_length > 0 && props.modelValue.length > 0 && props.modelValue.cargo_length > props.modelValue.length) ||
    (props.modelValue.cargo_width > 0 && props.modelValue.width > 0 && props.modelValue.cargo_width > props.modelValue.width) ||
    (props.modelValue.cargo_height > 0 && props.modelValue.height > 0 && props.modelValue.cargo_height > props.modelValue.height)
  )
})

// Display helpers
const axleLoadsDisplay = computed(() => {
  if (props.modelValue.axle_loads.length === 0) return '未设置'
  return props.modelValue.axle_loads.map((l, i) => `轴${i + 1}:${l}t`).join(', ')
})

const axleSpacingsDisplay = computed(() => {
  if (props.modelValue.axle_spacings.length === 0) return '未设置'
  return props.modelValue.axle_spacings.map((s, i) => `s${i + 1}:${s}m`).join(', ')
})

const totalAxleSpacing = computed(() => {
  return props.modelValue.axle_spacings.reduce((a, b) => a + b, 0)
})

function triggerSave() {
  emit('save')
}
</script>

<style scoped>
.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
