<template>
  <q-dialog v-model="showDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card class="bg-grey-1">
      <q-toolbar class="bg-primary text-white">
        <q-btn flat round dense icon="close" v-close-popup />
        <q-toolbar-title>车辆档案管理</q-toolbar-title>
        <q-btn flat label="保存" icon="save" @click="saveProfile" v-if="isEditing" />
      </q-toolbar>

      <q-card-section class="row q-col-gutter-md">
        <!-- Left: List of Profiles -->
        <div class="col-12 col-md-4">
          <q-card class="full-height">
            <q-card-section class="row items-center q-pb-none">
              <div class="text-h6">车辆列表</div>
              <q-space />
              <q-btn round color="primary" icon="add" size="sm" @click="createNew" />
            </q-card-section>
            <q-card-section>
              <q-list separator>
                <q-item 
                  v-for="vehicle in vehicles" 
                  :key="vehicle.id" 
                  clickable 
                  v-ripple
                  :active="currentVehicle && currentVehicle.id === vehicle.id"
                  active-class="bg-blue-1 text-primary"
                  @click="selectVehicle(vehicle)"
                >
                  <q-item-section avatar>
                    <q-icon name="local_shipping" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ vehicle.name }}</q-item-label>
                    <q-item-label caption>{{ vehicle.total_weight }}吨 | {{ vehicle.axis_count }}轴</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row">
                       <q-btn flat round dense icon="check" color="green" @click.stop="$emit('select', vehicle); showDialog = false">
                           <q-tooltip>选择此车</q-tooltip>
                       </q-btn>
                       <q-btn flat round dense icon="delete" color="red" @click.stop="confirmDelete(vehicle)" />
                    </div>
                  </q-item-section>
                </q-item>
                <q-item v-if="vehicles.length === 0">
                    <q-item-section class="text-center text-grey">暂无车辆档案，请点击右上角添加</q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>
        </div>

        <!-- Right: Editor Form -->
        <div class="col-12 col-md-8" v-if="currentVehicle">
          <q-card>
            <q-card-section>
              <div class="text-h6 q-mb-md">{{ isCreating ? '新建车辆' : '编辑车辆' }}</div>
              <q-form class="q-gutter-md">
                <!-- Basic Info -->
                <div class="row q-col-gutter-sm">
                    <div class="col-12 col-sm-6">
                        <q-input filled v-model="currentVehicle.name" label="档案名称" hint="如：150吨液压轴线车" :rules="[val => !!val || '必填']"/>
                    </div>
                    <div class="col-12 col-sm-6">
                         <q-input filled v-model="currentVehicle.license_plate" label="车牌号 (选填)" />
                    </div>
                </div>

                <!-- Dimensions -->
                <div class="text-subtitle2 text-primary q-mt-md">尺寸与重量</div>
                <div class="row q-col-gutter-sm">
                    <div class="col-6 col-sm-3">
                        <q-input filled v-model.number="currentVehicle.length" type="number" label="车长 (米)" :rules="[val => val > 0 || '无效']"/>
                    </div>
                    <div class="col-6 col-sm-3">
                        <q-input filled v-model.number="currentVehicle.width" type="number" label="车宽 (米)" :rules="[val => val > 0 || '无效']"/>
                    </div>
                    <div class="col-6 col-sm-3">
                        <q-input filled v-model.number="currentVehicle.height" type="number" label="车高 (米)" :rules="[val => val > 0 || '无效']"/>
                    </div>
                    <div class="col-6 col-sm-3">
                        <q-input filled v-model.number="currentVehicle.total_weight" type="number" label="车货总重 (吨)" :rules="[val => val > 0 || '无效']"/>
                    </div>
                </div>

                <!-- Axle Configuration -->
                <div class="text-subtitle2 text-primary q-mt-md row items-center">
                    轴组配置 
                    <q-badge color="orange" class="q-ml-sm">轴数: {{ axisWeights.length }}</q-badge>
                    <q-space />
                    <q-btn size="sm" color="secondary" label="添加轴" icon="add" @click="addAxis" />
                </div>
                
                <div class="row q-col-gutter-sm q-mt-xs">
                     <div class="col-12">
                         <q-banner class="bg-grey-2 q-mb-sm" rounded dense>
                             <template v-slot:avatar><q-icon name="info" color="primary"/></template>
                             请按顺序输入每一轴的轴重(吨)和与前一轴的轴距(米)。第一轴轴距默认为0。
                         </q-banner>
                     </div>
                     
                     <div v-for="(axis, index) in axisWeights" :key="index" class="col-12 row items-center q-col-gutter-x-sm q-mb-sm bg-grey-1 q-pa-xs rounded-borders">
                         <div class="col-auto text-bold text-grey-8">第{{ index + 1 }}轴</div>
                         <div class="col">
                             <q-input dense outlined v-model.number="axisWeights[index]" type="number" label="轴重(吨)" />
                         </div>
                         <div class="col" v-if="index > 0">
                             <q-input dense outlined v-model.number="axisDistances[index-1]" type="number" label="距前轴(米)" />
                         </div>
                         <div class="col-auto" v-if="index > 0">
                             <q-btn flat round color="red" icon="remove_circle" size="sm" @click="removeAxis(index)" />
                         </div>
                     </div>
                </div>

              </q-form>
            </q-card-section>
          </q-card>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { getVehicleProfiles, createVehicleProfile, updateVehicleProfile, deleteVehicleProfile } from '../api/vehicle'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'select'])

const $q = useQuasar()
const vehicles = ref([])
const currentVehicle = ref(null)
const isCreating = ref(false)

// Temp arrays for editing
const axisWeights = ref([])
const axisDistances = ref([])

const showDialog = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEditing = computed(() => !!currentVehicle.value)

const loadVehicles = async () => {
    try {
        vehicles.value = await getVehicleProfiles()
    } catch (e) {
        $q.notify({color: 'negative', message: '加载车辆列表失败'})
    }
}

const createNew = () => {
    isCreating.value = true
    currentVehicle.value = {
        name: '新车辆模板',
        length: 13,
        width: 2.5,
        height: 4,
        total_weight: 49,
        axis_count: 0
    }
    axisWeights.value = [6, 11, 11, 11, 11]
    axisDistances.value = [3.5, 1.4, 7, 1.4]
}

const selectVehicle = (vehicle) => {
    isCreating.value = false
    // Deep copy
    currentVehicle.value = JSON.parse(JSON.stringify(vehicle))
    axisWeights.value = [...vehicle.axis_weights]
    axisDistances.value = [...vehicle.axis_distances]
}

const addAxis = () => {
    axisWeights.value.push(10)
    if (axisWeights.value.length > 1) {
        axisDistances.value.push(1.4)
    }
}

const removeAxis = (index) => {
    axisWeights.value.splice(index, 1)
    if (index > 0) {
        axisDistances.value.splice(index - 1, 1)
    }
}

const saveProfile = async () => {
    // Validate
    if (axisWeights.value.length !== axisDistances.value.length + 1) {
        $q.notify({color: 'warning', message: '轴距数量应比轴数少1'})
        return
    }
    
    const payload = {
        ...currentVehicle.value,
        axis_count: axisWeights.value.length,
        axis_weights: axisWeights.value,
        axis_distances: axisDistances.value
    }
    
    try {
        if (isCreating.value) {
            await createVehicleProfile(payload)
            $q.notify({color: 'positive', message: '创建成功'})
        } else {
            const { id, ...updateData } = payload
            await updateVehicleProfile(id, updateData)
            $q.notify({color: 'positive', message: '更新成功'})
        }
        await loadVehicles()
        currentVehicle.value = null // Close editor
    } catch (e) {
        $q.notify({color: 'negative', message: '保存失败: ' + e.message})
    }
}

const confirmDelete = (vehicle) => {
    $q.dialog({
        title: '确认删除',
        message: `确定要删除 "${vehicle.name}" 吗？`,
        cancel: true,
        persistent: true
    }).onOk(async () => {
        try {
            await deleteVehicleProfile(vehicle.id)
            $q.notify({color: 'positive', message: '已删除'})
            if (currentVehicle.value && currentVehicle.value.id === vehicle.id) {
                currentVehicle.value = null
            }
            await loadVehicles()
        } catch (e) {
            $q.notify({color: 'negative', message: '删除失败'})
        }
    })
}

onMounted(() => {
    loadVehicles()
})

// Reload when dialog opens
watch(showDialog, (val) => {
    if (val) loadVehicles()
})
</script>
