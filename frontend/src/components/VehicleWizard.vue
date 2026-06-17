<template>
  <q-card class="bg-grey-1 vehicle-wizard" style="max-height: 95vh; display: flex; flex-direction: column;">
    <!-- Toolbar -->
    <q-toolbar class="bg-primary text-white">
      <q-btn flat round dense icon="close" @click="emit('close')" />
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
      <VehicleFormStep v-if="step === 1" v-model="wizard" />
      <AxleConfigStep v-if="step === 2" ref="axleStepRef" v-model="wizard" />
      <ReviewConfirmStep v-if="step === 3" v-model="wizard" />
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
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useQuasar } from 'quasar'
import VehicleFormStep from './VehicleFormStep.vue'
import AxleConfigStep from './AxleConfigStep.vue'
import ReviewConfirmStep from './ReviewConfirmStep.vue'

const emit = defineEmits(['complete', 'close', 'save'])
const $q = useQuasar()

const step = ref(1)
const totalSteps = 3
const axleStepRef = ref(null)

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

// Validation functions
function validateStep1() {
  if (!wizard.trailer_type) {
    $q.notify({ type: 'warning', message: '请选择挂车类型' })
    return false
  }
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

function validateStep2() {
  if (axleStepRef.value) {
    const result = axleStepRef.value.validate()
    if (!result.valid) {
      $q.notify({ type: 'warning', message: result.errors[0] || '轴距配置有误' })
      return false
    }
  }
  return true
}

function validateStep3() {
  if (!wizard.cargo_name) {
    $q.notify({ type: 'warning', message: '请填写货物名称' })
    return false
  }
  return true
}

const stepValidators = [null, validateStep1, validateStep2, validateStep3]

function nextStep() {
  if (step.value <= totalSteps) {
    const validator = stepValidators[step.value]
    if (validator && !validator()) return
  }
  if (step.value < totalSteps) {
    step.value++
    // When entering step 2, sync data to axle configurator
    if (step.value === 2 && axleStepRef.value) {
      axleStepRef.value.syncToConfigurator()
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
  emit('save', vehicle)
  emit('close')

  $q.notify({
    type: 'positive',
    message: '车辆参数配置完成',
    icon: 'check_circle',
    position: 'top'
  })
}
</script>

<style scoped>
.vehicle-wizard {
  min-width: 320px;
}
</style>
