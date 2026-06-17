<template>
  <div class="step-content">
    <!-- Vehicle Type Selection -->
    <div class="text-h5 q-mb-sm">选择挂车类型</div>
    <div class="text-body1 text-grey-7 q-mb-lg">
      请根据实际运输配置选择对应的车辆组合类型
    </div>

    <div class="row q-col-gutter-md">
      <div
        v-for="(vt, idx) in vehicleTypes"
        :key="idx"
        class="col-12 col-md-4"
      >
        <q-card
          :class="['type-card', { selected: modelValue.trailer_type === vt.value }]"
          @click="modelValue.trailer_type = vt.value"
          flat
          bordered
        >
          <q-card-section horizontal>
            <!-- SVG Icon -->
            <div class="type-icon" v-html="vt.icon" />
            <q-card-section>
              <div class="text-h6">{{ vt.label }}</div>
              <div class="text-caption text-grey-7 q-mt-sm">{{ vt.desc }}</div>
              <div class="text-caption text-grey-7 q-mt-xs">
                适用: {{ vt.applicable }}
              </div>
            </q-card-section>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div v-if="modelValue.trailer_type" class="q-mt-lg">
      <q-banner rounded class="bg-blue-1 text-primary">
        <template v-slot:avatar>
          <q-icon name="info" />
        </template>
        已选择: <strong>{{ selectedTypeName }}</strong>
      </q-banner>
    </div>
    <div v-else class="q-mt-lg">
      <q-banner rounded class="bg-orange-1">
        请选择一种挂车类型以继续
      </q-banner>
    </div>

    <q-separator class="q-my-xl" />

    <!-- Basic Dimensions -->
    <div class="text-h5 q-mb-sm">车辆尺寸参数</div>
    <div class="text-body1 text-grey-7 q-mb-md">
      请填写车货总体的外廓尺寸和车辆分段尺寸
    </div>

    <!-- Dimension diagram -->
    <div class="dimension-diagram q-mb-lg">
      <svg viewBox="0 0 800 280" xmlns="http://www.w3.org/2000/svg" class="dim-svg">
        <!-- Vehicle top-down view -->
        <rect x="60" y="30" :width="lengthPx" height="100" rx="6" fill="#e3f2fd" stroke="#1976d2" stroke-width="2" />
        <!-- Tractor section -->
        <rect x="60" y="30" :width="tractorLenPx" height="100" rx="6" fill="#bbdefb" stroke="#1976d2" stroke-width="2" />
        <!-- Divider -->
        <line :x1="60 + tractorLenPx" y1="30" :x2="60 + tractorLenPx" y2="130" stroke="#1976d2" stroke-width="1.5" stroke-dasharray="6,4" />
        <!-- Trailer label -->
        <text :x="60 + tractorLenPx / 2" y="85" text-anchor="middle" font-size="13" fill="#1565c0" font-weight="bold">牵引车</text>
        <text :x="60 + tractorLenPx + (lengthPx - tractorLenPx) / 2" y="85" text-anchor="middle" font-size="13" fill="#0d47a1" font-weight="bold">挂车</text>

        <!-- Length dimension arrow (top) -->
        <line x1="60" y1="18" :x2="60 + lengthPx" y2="18" stroke="#e65100" stroke-width="1.5" />
        <line x1="60" y1="15" x2="60" y2="21" stroke="#e65100" stroke-width="1.5" />
        <line :x1="60 + lengthPx" y1="15" :x2="60 + lengthPx" y2="21" stroke="#e65100" stroke-width="1.5" />
        <text :x="60 + lengthPx / 2" y="14" text-anchor="middle" font-size="12" fill="#e65100" font-weight="bold">总长 {{ modelValue.length || '?' }}m</text>

        <!-- Tractor length arrow -->
        <line x1="60" y1="138" :x2="60 + tractorLenPx" y2="138" stroke="#ef6c00" stroke-width="1" />
        <line x1="60" y1="135" x2="60" y2="141" stroke="#ef6c00" stroke-width="1" />
        <line :x1="60 + tractorLenPx" y1="135" :x2="60 + tractorLenPx" y2="141" stroke="#ef6c00" stroke-width="1" />
        <text :x="60 + tractorLenPx / 2" y="152" text-anchor="middle" font-size="11" fill="#ef6c00">牵引车 {{ modelValue.tractor_length || '?' }}m</text>

        <!-- Trailer length arrow -->
        <line :x1="60 + tractorLenPx" y1="138" :x2="60 + lengthPx" y2="138" stroke="#ef6c00" stroke-width="1" />
        <line :x1="60 + tractorLenPx" y1="135" :x2="60 + tractorLenPx" y2="141" stroke="#ef6c00" stroke-width="1" />
        <line :x1="60 + lengthPx" y1="135" :x2="60 + lengthPx" y2="141" stroke="#ef6c00" stroke-width="1" />
        <text :x="60 + tractorLenPx + (lengthPx - tractorLenPx) / 2" y="152" text-anchor="middle" font-size="11" fill="#ef6c00">挂车 {{ modelValue.trailer_length || '?' }}m</text>

        <!-- Width arrow (right side) -->
        <line :x1="60 + lengthPx + 20" y1="30" :x2="60 + lengthPx + 20" y2="130" stroke="#2e7d32" stroke-width="1.5" />
        <line :x1="60 + lengthPx + 17" y1="30" :x2="60 + lengthPx + 23" y2="30" stroke="#2e7d32" stroke-width="1.5" />
        <line :x1="60 + lengthPx + 17" y1="130" :x2="60 + lengthPx + 23" y2="130" stroke="#2e7d32" stroke-width="1.5" />
        <text :x="60 + lengthPx + 40" y="84" text-anchor="middle" font-size="12" fill="#2e7d32" font-weight="bold" :transform="`rotate(-90, ${60 + lengthPx + 40}, 84)`">宽度 {{ modelValue.width || '?' }}m</text>
      </svg>
    </div>

    <div class="row q-col-gutter-sm">
      <div class="col-6 col-md-4">
        <q-input
          filled
          v-model.number="modelValue.length"
          type="number"
          label="车货总长度"
          suffix="m"
          step="0.1"
          min="1"
          :rules="[val => val > 0 || '必填']"
        />
      </div>
      <div class="col-6 col-md-4">
        <q-input
          filled
          v-model.number="modelValue.width"
          type="number"
          label="车货总宽度"
          suffix="m"
          step="0.1"
          min="1"
          :rules="[val => val > 0 || '必填']"
        />
      </div>
      <div class="col-6 col-md-4">
        <q-input
          filled
          v-model.number="modelValue.height"
          type="number"
          label="车货总高度"
          suffix="m"
          step="0.1"
          min="1"
          :rules="[val => val > 0 || '必填']"
        />
      </div>
      <div class="col-6 col-md-4">
        <q-input
          filled
          v-model.number="modelValue.tractor_length"
          type="number"
          label="牵引车长度"
          suffix="m"
          step="0.1"
          min="1"
          :rules="[val => val > 0 || '必填']"
          hint="车头最前端到挂车连接点"
        />
      </div>
      <div class="col-6 col-md-4">
        <q-input
          filled
          v-model.number="modelValue.trailer_length"
          type="number"
          label="挂车长度"
          suffix="m"
          step="0.1"
          min="1"
          :rules="[val => val > 0 || '必填']"
        />
      </div>
    </div>

    <q-banner rounded class="bg-grey-3 q-mt-md">
      <template v-slot:avatar>
        <q-icon name="lightbulb" color="orange" />
      </template>
      提示: 牵引车长度指从车辆最前端到挂车连接点的距离；挂车长度指连接点至挂车尾部的距离。两者之和应等于总长度。
    </q-banner>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true }
})

const emit = defineEmits(['update:modelValue'])

// Vehicle type SVGs
const vehicleTypes = [
  {
    value: 'lowbed',
    label: '低平板半挂车',
    desc: '牵引车 + 低平板半挂车组合，适用于常规大件运输。半挂车具有低平板结构，方便装卸货物。',
    applicable: '风电叶片、塔筒、变压器等常规大件',
    icon: `<svg width="160" height="90" viewBox="0 0 200 90" xmlns="http://www.w3.org/2000/svg">
      <rect x="15" y="30" width="70" height="45" rx="5" fill="#1976d2" opacity="0.9"/>
      <rect x="25" y="35" width="25" height="20" rx="2" fill="#bbdefb"/>
      <circle cx="30" cy="78" r="7" fill="#333"/>
      <circle cx="50" cy="78" r="7" fill="#333"/>
      <circle cx="75" cy="78" r="7" fill="#333"/>
      <rect x="88" y="55" width="100" height="25" rx="3" fill="#0d47a1"/>
      <rect x="90" y="55" width="20" height="25" fill="#1565c0"/>
      <rect x="95" y="58" width="15" height="10" rx="1" fill="#e3f2fd"/>
      <circle cx="125" cy="83" r="7" fill="#333"/>
      <circle cx="145" cy="83" r="7" fill="#333"/>
      <circle cx="165" cy="83" r="7" fill="#333"/>
      <circle cx="180" cy="83" r="7" fill="#333"/>
    </svg>`
  },
  {
    value: 'hydraulic',
    label: '多轴液压悬挂挂车',
    desc: '牵引车 + 多轴多轮液压悬挂挂车，适用于超重超大件运输。液压悬挂系统可实现轴重自动均衡。',
    applicable: '超重变压器、大型发电机定子等',
    icon: `<svg width="160" height="90" viewBox="0 0 200 90" xmlns="http://www.w3.org/2000/svg">
      <rect x="15" y="30" width="70" height="45" rx="5" fill="#1976d2" opacity="0.9"/>
      <rect x="25" y="35" width="25" height="20" rx="2" fill="#bbdefb"/>
      <circle cx="30" cy="78" r="7" fill="#333"/>
      <circle cx="50" cy="78" r="7" fill="#333"/>
      <circle cx="75" cy="78" r="7" fill="#333"/>
      <rect x="88" y="52" width="105" height="28" rx="3" fill="#2e7d32"/>
      <circle cx="105" cy="83" r="7" fill="#333"/>
      <circle cx="118" cy="83" r="7" fill="#333"/>
      <circle cx="131" cy="83" r="7" fill="#333"/>
      <circle cx="144" cy="83" r="7" fill="#333"/>
      <circle cx="157" cy="83" r="7" fill="#333"/>
      <circle cx="170" cy="83" r="7" fill="#333"/>
      <circle cx="183" cy="83" r="7" fill="#333"/>
      <text x="140" y="70" text-anchor="middle" font-size="10" fill="white" font-weight="bold">液压悬挂</text>
    </svg>`
  },
  {
    value: 'combo',
    label: '特殊组合液压悬挂挂车',
    desc: '牵引车 + 特殊组合液压悬挂挂车，适用于超长超大件。多模块拼接，可灵活调整挂车长度和轴数。',
    applicable: '超长风电叶片(>70m)、大型桥梁构件等',
    icon: `<svg width="160" height="90" viewBox="0 0 200 90" xmlns="http://www.w3.org/2000/svg">
      <rect x="15" y="30" width="70" height="45" rx="5" fill="#1976d2" opacity="0.9"/>
      <rect x="25" y="35" width="25" height="20" rx="2" fill="#bbdefb"/>
      <circle cx="30" cy="78" r="7" fill="#333"/>
      <circle cx="50" cy="78" r="7" fill="#333"/>
      <circle cx="75" cy="78" r="7" fill="#333"/>
      <rect x="88" y="50" width="45" height="30" rx="3" fill="#e65100"/>
      <rect x="135" y="50" width="45" height="30" rx="3" fill="#e65100"/>
      <line x1="133" y1="65" x2="135" y2="65" stroke="#bf360c" stroke-width="2"/>
      <circle cx="100" cy="83" r="7" fill="#333"/>
      <circle cx="113" cy="83" r="7" fill="#333"/>
      <circle cx="126" cy="83" r="7" fill="#333"/>
      <circle cx="147" cy="83" r="7" fill="#333"/>
      <circle cx="160" cy="83" r="7" fill="#333"/>
      <circle cx="173" cy="83" r="7" fill="#333"/>
      <text x="110" y="70" text-anchor="middle" font-size="9" fill="white" font-weight="bold">模块1</text>
      <text x="157" y="70" text-anchor="middle" font-size="9" fill="white" font-weight="bold">模块2</text>
    </svg>`
  }
]

const selectedTypeName = computed(() => {
  const vt = vehicleTypes.find(t => t.value === props.modelValue.trailer_type)
  return vt ? vt.label : ''
})

// Dimension diagram helpers
const lengthPx = computed(() => {
  const len = props.modelValue.length || 24
  return (len / 30) * 500
})

const tractorLenPx = computed(() => {
  const tLen = props.modelValue.tractor_length || 8
  const total = props.modelValue.length || 24
  if (total <= 0) return 100
  return lengthPx.value * (tLen / total)
})
</script>

<style scoped>
.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.type-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.type-card:hover {
  border-color: #90caf9;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
}

.type-card.selected {
  border-color: #1976d2;
  background: #e3f2fd;
  box-shadow: 0 2px 12px rgba(25, 118, 210, 0.3);
}

.type-icon {
  flex-shrink: 0;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dimension-diagram {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px;
  overflow-x: auto;
}

.dim-svg {
  width: 100%;
  min-width: 400px;
  height: auto;
  display: block;
}
</style>
