<template>
  <q-dialog v-model="showDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card class="bg-grey-1 vehicle-wizard">
      <!-- Toolbar -->
      <q-toolbar class="bg-primary text-white">
        <q-btn flat round dense icon="close" v-close-popup />
        <q-toolbar-title>车辆参数配置向导</q-toolbar-title>
        <q-space />
        <q-btn
          flat
          :label="step > 1 ? '上一步' : ''"
          :icon="step > 1 ? 'arrow_back' : ''"
          @click="prevStep"
          :disable="step <= 1"
        />
        <div class="q-mx-sm text-caption">
          {{ step }} / {{ totalSteps }}
        </div>
        <q-btn
          v-if="step < totalSteps"
          flat
          label="下一步"
          icon-right="arrow_forward"
          color="white"
          @click="nextStep"
        />
        <q-btn
          v-else
          flat
          label="完成配置"
          icon="check_circle"
          color="white"
          @click="finish"
        />
      </q-toolbar>

      <q-card-section class="q-pa-lg" style="max-height: calc(100vh - 120px); overflow-y: auto;">
        <!-- Step 1: Vehicle Type Selection -->
        <div v-if="step === 1" class="step-content">
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
                :class="['type-card', { selected: wizard.trailer_type === vt.value }]"
                @click="wizard.trailer_type = vt.value"
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

          <div v-if="wizard.trailer_type" class="q-mt-lg">
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
        </div>

        <!-- Step 2: Basic Dimensions -->
        <div v-if="step === 2" class="step-content">
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
              <text :x="60 + lengthPx / 2" y="14" text-anchor="middle" font-size="12" fill="#e65100" font-weight="bold">总长 {{ wizard.length || '?' }}m</text>

              <!-- Tractor length arrow -->
              <line x1="60" y1="138" :x2="60 + tractorLenPx" y2="138" stroke="#ef6c00" stroke-width="1" />
              <line x1="60" y1="135" x2="60" y2="141" stroke="#ef6c00" stroke-width="1" />
              <line :x1="60 + tractorLenPx" y1="135" :x2="60 + tractorLenPx" y2="141" stroke="#ef6c00" stroke-width="1" />
              <text :x="60 + tractorLenPx / 2" y="152" text-anchor="middle" font-size="11" fill="#ef6c00">牵引车 {{ wizard.tractor_length || '?' }}m</text>

              <!-- Trailer length arrow -->
              <line :x1="60 + tractorLenPx" y1="138" :x2="60 + lengthPx" y2="138" stroke="#ef6c00" stroke-width="1" />
              <line :x1="60 + tractorLenPx" y1="135" :x2="60 + tractorLenPx" y2="141" stroke="#ef6c00" stroke-width="1" />
              <line :x1="60 + lengthPx" y1="135" :x2="60 + lengthPx" y2="141" stroke="#ef6c00" stroke-width="1" />
              <text :x="60 + tractorLenPx + (lengthPx - tractorLenPx) / 2" y="152" text-anchor="middle" font-size="11" fill="#ef6c00">挂车 {{ wizard.trailer_length || '?' }}m</text>

              <!-- Width arrow (right side) -->
              <line :x1="60 + lengthPx + 20" y1="30" :x2="60 + lengthPx + 20" y2="130" stroke="#2e7d32" stroke-width="1.5" />
              <line :x1="60 + lengthPx + 17" y1="30" :x2="60 + lengthPx + 23" y2="30" stroke="#2e7d32" stroke-width="1.5" />
              <line :x1="60 + lengthPx + 17" y1="130" :x2="60 + lengthPx + 23" y2="130" stroke="#2e7d32" stroke-width="1.5" />
              <text :x="60 + lengthPx + 40" y="84" text-anchor="middle" font-size="12" fill="#2e7d32" font-weight="bold" transform="rotate(-90, 60+lengthPx+40, 84)">宽度 {{ wizard.width || '?' }}m</text>
            </svg>
          </div>

          <div class="row q-col-gutter-sm">
            <div class="col-6 col-md-4">
              <q-input
                filled
                v-model.number="wizard.length"
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
                v-model.number="wizard.width"
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
                v-model.number="wizard.height"
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
                v-model.number="wizard.tractor_length"
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
                v-model.number="wizard.trailer_length"
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

        <!-- Step 3: Weight Configuration -->
        <div v-if="step === 3" class="step-content">
          <div class="text-h5 q-mb-sm">重量与轴数配置</div>
          <div class="text-body1 text-grey-7 q-mb-md">
            填写车货总重和轴数，系统将帮助您分配轴重
          </div>

          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-input
                filled
                v-model.number="wizard.total_weight"
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
                v-model.number="wizard.axle_count"
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
          <div v-if="wizard.total_weight > 0 && wizard.axle_count > 0" class="q-mb-md">
            <div class="text-subtitle2 q-mb-xs">轴重分布预览</div>
            <div class="weight-bar-container">
              <div
                v-for="i in wizard.axle_count"
                :key="i"
                class="weight-bar-segment"
                :style="{ width: (100 / wizard.axle_count) + '%' }"
              >
                <div class="weight-bar-fill" />
                <div class="weight-bar-label">轴{{ i }}</div>
                <div class="weight-bar-value">{{ (wizard.total_weight / wizard.axle_count).toFixed(1) }}t</div>
              </div>
            </div>
            <div class="text-caption text-grey-6 q-mt-xs">
              均匀分配: 每轴 {{ (wizard.total_weight / wizard.axle_count).toFixed(1) }} 吨 (可在下一步调整)
            </div>
          </div>

          <!-- Axle Load Quick Entry -->
          <div v-if="wizard.axle_count >= 2" class="q-mt-lg">
            <div class="text-subtitle2 q-mb-sm">轴重快速设置 (吨)</div>
            <div class="row q-col-gutter-sm">
              <div
                v-for="i in Math.min(wizard.axle_count, 10)"
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
        </div>

        <!-- Step 4: Axle Spacing Configuration -->
        <div v-if="step === 4" class="step-content">
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

        <!-- Step 5: Cargo Information -->
        <div v-if="step === 5" class="step-content">
          <div class="text-h5 q-mb-sm">货物信息</div>
          <div class="text-body1 text-grey-7 q-mb-md">
            填写运输货物的详细信息
          </div>

          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-input
                filled
                v-model="wizard.cargo_name"
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
                v-model.number="wizard.cargo_weight"
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
                v-model.number="wizard.cargo_length"
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
                v-model.number="wizard.cargo_width"
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
                v-model.number="wizard.cargo_height"
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
            <span v-if="wizard.cargo_length > wizard.length">
              货物长度({{ wizard.cargo_length }}m)超过车货总长({{ wizard.length }}m)，请检查
            </span>
            <span v-else-if="wizard.cargo_width > wizard.width">
              货物宽度({{ wizard.cargo_width }}m)超过车货总宽({{ wizard.width }}m)，请检查
            </span>
            <span v-else-if="wizard.cargo_height > wizard.height">
              货物高度({{ wizard.cargo_height }}m)超过车货总高({{ wizard.height }}m)，请检查
            </span>
          </q-banner>
        </div>

        <!-- Step 6: Summary & Confirmation -->
        <div v-if="step === 6" class="step-content">
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
                      <div class="text-h6">{{ wizard.length || '-' }}<span class="text-caption">m</span></div>
                    </div>
                    <div class="col-4 text-center">
                      <div class="text-caption text-grey-7">总宽</div>
                      <div class="text-h6">{{ wizard.width || '-' }}<span class="text-caption">m</span></div>
                    </div>
                    <div class="col-4 text-center">
                      <div class="text-caption text-grey-7">总高</div>
                      <div class="text-h6">{{ wizard.height || '-' }}<span class="text-caption">m</span></div>
                    </div>
                  </div>
                  <q-separator class="q-my-sm" />
                  <div class="row text-center">
                    <div class="col-6">
                      <div class="text-caption text-grey-7">牵引车长</div>
                      <div class="text-body1">{{ wizard.tractor_length || '-' }}m</div>
                    </div>
                    <div class="col-6">
                      <div class="text-caption text-grey-7">挂车长</div>
                      <div class="text-body1">{{ wizard.trailer_length || '-' }}m</div>
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
                      <div class="text-h6">{{ wizard.total_weight || '-' }}<span class="text-caption">t</span></div>
                    </div>
                    <div class="col-6 text-center">
                      <div class="text-caption text-grey-7">总轴数</div>
                      <div class="text-h6">{{ wizard.axle_count || '-' }}<span class="text-caption">轴</span></div>
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
                  <div class="text-caption text-grey-7 q-mt-sm">轴距分布 (共{{ wizard.axle_spacings.length }}段)</div>
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
                  <div class="text-body1 q-mt-sm">{{ wizard.cargo_name || '-' }}</div>
                  <div class="row q-mt-xs">
                    <div class="col-4 text-center">
                      <div class="text-caption text-grey-7">长</div>
                      <div class="text-body2">{{ wizard.cargo_length || '-' }}m</div>
                    </div>
                    <div class="col-4 text-center">
                      <div class="text-caption text-grey-7">宽</div>
                      <div class="text-body2">{{ wizard.cargo_width || '-' }}m</div>
                    </div>
                    <div class="col-4 text-center">
                      <div class="text-caption text-grey-7">高</div>
                      <div class="text-body2">{{ wizard.cargo_height || '-' }}m</div>
                    </div>
                  </div>
                  <div class="text-body2 q-mt-sm">货物重量: {{ wizard.cargo_weight || '-' }}t</div>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </div>
      </q-card-section>

      <!-- Stepper dots at bottom -->
      <q-card-section class="q-pa-sm bg-grey-2">
        <div class="row items-center justify-center q-gutter-x-sm">
          <q-btn
            v-for="s in totalSteps"
            :key="s"
            round
            :color="step >= s ? 'primary' : 'grey-5'"
            :text-color="step >= s ? 'white' : 'grey-7'"
            :label="String(s)"
            size="sm"
            unelevated
            @click="goToStep(s)"
            :disable="s > step && !canProceed(s)"
          />
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import AxleConfigurator from './AxleConfigurator.vue'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'complete'])
const $q = useQuasar()

const showDialog = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const step = ref(1)
const totalSteps = 6
const axleConfigRef = ref(null)

// Wizard data
const wizard = reactive({
  trailer_type: '',
  length: null,
  width: null,
  height: null,
  tractor_length: null,
  trailer_length: null,
  total_weight: null,
  axle_count: null,
  axle_loads: [],
  axle_spacings: [],
  cargo_name: '',
  cargo_length: null,
  cargo_width: null,
  cargo_height: null,
  cargo_weight: null
})

// Local axle loads for quick entry in step 3
const axleLoadsLocal = ref([])

// Watch axle_count to resize axleLoadsLocal
watch(() => wizard.axle_count, (count) => {
  if (!count) {
    axleLoadsLocal.value = []
    return
  }
  const newLoads = []
  const evenLoad = wizard.total_weight ? parseFloat((wizard.total_weight / count).toFixed(2)) : 0
  for (let i = 0; i < count; i++) {
    newLoads.push(axleLoadsLocal.value[i] || evenLoad)
  }
  axleLoadsLocal.value = newLoads
})

// Watch total_weight to auto-distribute
watch(() => wizard.total_weight, (weight) => {
  if (wizard.axle_count && weight) {
    const evenLoad = parseFloat((weight / wizard.axle_count).toFixed(2))
    for (let i = 0; i < axleLoadsLocal.value.length; i++) {
      if (!axleLoadsLocal.value[i]) {
        axleLoadsLocal.value[i] = evenLoad
      }
    }
  }
})

// Axle config for the AxleConfigurator component (step 4)
const axleConfig = computed({
  get: () => ({
    axleCount: wizard.axle_count || 5,
    spacings: wizard.axle_spacings.length > 0 ? [...wizard.axle_spacings] : defaultSpacings(),
    axleLoads: wizard.axle_loads.length > 0 ? [...wizard.axle_loads] : defaultLoads(),
    totalWeight: wizard.total_weight || 150,
    tractorLength: wizard.tractor_length || 8,
    trailerLength: wizard.trailer_length || 16
  }),
  set: (val) => {
    if (val.axleCount != null) wizard.axle_count = val.axleCount
    if (val.spacings) wizard.axle_spacings = [...val.spacings]
    if (val.axleLoads) wizard.axle_loads = [...val.axleLoads]
    if (val.totalWeight != null) wizard.total_weight = val.totalWeight
    if (val.tractorLength != null) wizard.tractor_length = val.tractorLength
    if (val.trailerLength != null) wizard.trailer_length = val.trailerLength
  }
})

function defaultSpacings() {
  const count = wizard.axle_count || 5
  if (count <= 2) return [1.4]
  // Some reasonable defaults based on vehicle type
  const spacings = []
  for (let i = 0; i < count - 1; i++) {
    spacings.push(i === 0 ? 3.2 : i < 3 ? 1.45 : 1.4)
  }
  return spacings
}

function defaultLoads() {
  const count = wizard.axle_count || 5
  const total = wizard.total_weight || 150
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

// Step 1: Vehicle type SVGs
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
  const vt = vehicleTypes.find(t => t.value === wizard.trailer_type)
  return vt ? vt.label : ''
})

// Step 2: Dimension diagram helpers
const lengthPx = computed(() => {
  const len = wizard.length || 24
  return (len / 30) * 500
})

const tractorLenPx = computed(() => {
  const tLen = wizard.tractor_length || 8
  const total = wizard.length || 24
  if (total <= 0) return 100
  return lengthPx.value * (tLen / total)
})

// Step 5: Cargo size check
const hasCargoSizeIssue = computed(() => {
  return (
    (wizard.cargo_length > 0 && wizard.length > 0 && wizard.cargo_length > wizard.length) ||
    (wizard.cargo_width > 0 && wizard.width > 0 && wizard.cargo_width > wizard.width) ||
    (wizard.cargo_height > 0 && wizard.height > 0 && wizard.cargo_height > wizard.height)
  )
})

// Step 6: Display helpers
const axleLoadsDisplay = computed(() => {
  if (wizard.axle_loads.length === 0) return '未设置'
  return wizard.axle_loads.map((l, i) => `轴${i + 1}:${l}t`).join(', ')
})

const axleSpacingsDisplay = computed(() => {
  if (wizard.axle_spacings.length === 0) return '未设置'
  return wizard.axle_spacings.map((s, i) => `s${i + 1}:${s}m`).join(', ')
})

const totalAxleSpacing = computed(() => {
  return wizard.axle_spacings.reduce((a, b) => a + b, 0)
})

// Validation
function validateStep1() {
  if (!wizard.trailer_type) {
    $q.notify({ type: 'warning', message: '请选择挂车类型' })
    return false
  }
  return true
}

function validateStep2() {
  const fields = [
    { val: wizard.length, name: '车货总长度' },
    { val: wizard.width, name: '车货总宽度' },
    { val: wizard.height, name: '车货总高度' },
    { val: wizard.tractor_length, name: '牵引车长度' },
    { val: wizard.trailer_length, name: '挂车长度' }
  ]
  for (const f of fields) {
    if (!f.val || f.val <= 0) {
      $q.notify({ type: 'warning', message: `请填写${f.name}` })
      return false
    }
  }
  return true
}

function validateStep3() {
  if (!wizard.total_weight || wizard.total_weight <= 0) {
    $q.notify({ type: 'warning', message: '请填写车货总质量' })
    return false
  }
  if (!wizard.axle_count || wizard.axle_count < 2) {
    $q.notify({ type: 'warning', message: '轴数至少为2' })
    return false
  }
  return true
}

function validateStep4() {
  if (axleConfigRef.value) {
    const result = axleConfigRef.value.validate()
    if (!result.valid) {
      $q.notify({ type: 'warning', message: result.errors[0] || '轴距配置有误' })
      return false
    }
  }
  // Sync axle loads from step 3 quick entry if not set via configurator
  if (wizard.axle_loads.length === 0) {
    wizard.axle_loads = [...axleLoadsLocal.value]
  }
  return true
}

function validateStep5() {
  if (!wizard.cargo_name) {
    $q.notify({ type: 'warning', message: '请填写货物名称' })
    return false
  }
  return true
}

const stepValidators = [null, validateStep1, validateStep2, validateStep3, validateStep4, validateStep5]

function nextStep() {
  if (step.value <= totalSteps) {
    const validator = stepValidators[step.value]
    if (validator && !validator()) return
  }
  if (step.value < totalSteps) {
    step.value++
    // When entering step 4, sync data to axle configurator
    if (step.value === 4) {
      // Ensure defaults
      if (wizard.axle_spacings.length === 0) {
        wizard.axle_spacings = defaultSpacings()
      }
      if (wizard.axle_loads.length === 0) {
        wizard.axle_loads = [...axleLoadsLocal.value]
      }
    }
  }
}

function prevStep() {
  if (step.value > 1) step.value--
}

function goToStep(s) {
  if (s >= step.value || canProceed(s)) {
    step.value = s
  }
}

function canProceed(s) {
  if (s <= step.value) return true
  // Allow going to any step that's already been passed (for review)
  return false
}

function finish() {
  // Final validation
  for (let i = 1; i <= totalSteps; i++) {
    const validator = stepValidators[i]
    if (validator && !validator()) {
      step.value = i
      return
    }
  }

  // Build vehicle object
  const vehicle = {
    trailer_type: wizard.trailer_type,
    length: wizard.length,
    width: wizard.width,
    height: wizard.height,
    total_weight: wizard.total_weight,
    axle_count: wizard.axle_count,
    axle_loads: [...wizard.axle_loads],
    axle_spacings: [...wizard.axle_spacings],
    tractor_length: wizard.tractor_length,
    trailer_length: wizard.trailer_length,
    cargo_name: wizard.cargo_name,
    cargo_length: wizard.cargo_length,
    cargo_width: wizard.cargo_width,
    cargo_height: wizard.cargo_height,
    cargo_weight: wizard.cargo_weight
  }

  emit('complete', vehicle)
  showDialog.value = false

  $q.notify({
    type: 'positive',
    message: '车辆参数配置完成',
    icon: 'check_circle',
    position: 'top'
  })
}

// Watch dialog close
watch(showDialog, (val) => {
  if (val) {
    // Reset on open
    step.value = 1
  }
})
</script>

<style scoped>
.vehicle-wizard {
  min-width: 320px;
}

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
