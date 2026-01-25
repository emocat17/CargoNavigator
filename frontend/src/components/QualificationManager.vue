<template>
  <q-dialog v-model="showDialog" persistent maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card class="bg-grey-1">
      <q-toolbar class="bg-primary text-white">
        <q-btn flat round dense icon="close" v-close-popup />
        <q-toolbar-title>通行资质预审信息录入</q-toolbar-title>
        <q-btn flat label="同步规划数据" icon="sync" @click="syncFromRoutePlan" class="q-mr-sm" />
        <q-btn flat label="保存" icon="save" @click="saveData" />
      </q-toolbar>

      <q-card-section class="q-pa-md">
        <div class="row q-col-gutter-md">
          <!-- Left: Navigation/Steps -->
          <div class="col-12 col-md-3">
            <q-card>
              <q-tabs
                v-model="tab"
                vertical
                class="text-primary"
              >
                <q-tab name="vehicle" icon="local_shipping" label="车辆与设备" />
                <q-tab name="owner" icon="business" label="业户与经办人" />
                <q-tab name="cargo" icon="inventory_2" label="货物与载重" />
                <q-tab name="plan" icon="map" label="运输计划" />
              </q-tabs>
            </q-card>
          </div>

          <!-- Right: Form Content -->
          <div class="col-12 col-md-9">
            <q-tab-panels v-model="tab" animated swipeable vertical transition-prev="jump-up" transition-next="jump-up">
              
              <!-- Tab 1: Vehicle & Equipment -->
              <q-tab-panel name="vehicle">
                <div class="text-h6 q-mb-md">车辆与设备配置</div>
                <q-form class="q-gutter-md">
                   <div class="text-subtitle2 text-primary">牵引车/运输车信息</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.tractor_plate_number" label="车辆牌号" :rules="[rules.required]" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.tractor_model" label="厂牌型号" :rules="[rules.required]" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model.number="formData.tractor_cur_weight" type="number" label="整备质量 (吨)" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.tractor_owner" label="所有人" /></div>
                       <div class="col-12">
                           <q-file filled v-model="formData.tractor_licence_image_arr" label="车辆行驶证 (图片)" multiple accept="image/*">
                               <template v-slot:append>
                                   <q-icon v-if="formData.tractor_licence_image_arr" name="close" @click.stop.prevent="formData.tractor_licence_image_arr = null" class="cursor-pointer" />
                               </template>
                           </q-file>
                       </div>
                   </div>

                   <div class="text-subtitle2 text-primary q-mt-md">挂车信息</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.trailer_plate_number" label="挂车牌号" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.trailer_model" label="厂牌型号" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model.number="formData.trailer_cur_weight" type="number" label="整备质量 (吨)" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.trailer_owner" label="挂车所有人" /></div>
                       <div class="col-12">
                           <q-file filled v-model="formData.trailer_licence_image_arr" label="挂车行驶证 (图片)" multiple accept="image/*">
                               <template v-slot:append>
                                   <q-icon v-if="formData.trailer_licence_image_arr" name="close" @click.stop.prevent="formData.trailer_licence_image_arr = null" class="cursor-pointer" />
                               </template>
                           </q-file>
                       </div>
                   </div>

                   <div class="text-subtitle2 text-primary q-mt-md">轴胎规格</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6"><q-input filled v-model.number="formData.axle_count" type="number" label="轴数" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model.number="formData.tire_count" type="number" label="轮胎数" /></div>
                       <div class="col-12"><q-input filled v-model="formData.axis_weights_str" label="轴重分布 (吨)" hint="以逗号分隔，如: 10,15,12" :rules="[rules.axisWeights]" /></div>
                       <div class="col-12"><q-input filled v-model="formData.axis_distances_str" label="轴距分布 (米)" hint="以逗号分隔，如: 3.5,1.2" :rules="[rules.axisDistances]" /></div>
                   </div>
                </q-form>
              </q-tab-panel>

              <!-- Tab 2: Owner & Handler -->
              <q-tab-panel name="owner">
                <div class="text-h6 q-mb-md">业户与经办人信息</div>
                <q-form class="q-gutter-md">
                   <div class="text-subtitle2 text-primary">业户信息</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12"><q-input filled v-model="formData.entity_name" label="业户名称" :rules="[rules.required]" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.entity_license_number" label="道路运输经营许可证号" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.entity_address" label="地址" /></div>
                       <div class="col-12">
                           <q-file filled v-model="formData.entity_license_image_arr" label="许可证图片" multiple accept="image/*">
                               <template v-slot:append>
                                   <q-icon v-if="formData.entity_license_image_arr" name="close" @click.stop.prevent="formData.entity_license_image_arr = null" class="cursor-pointer" />
                               </template>
                           </q-file>
                       </div>
                   </div>

                   <div class="text-subtitle2 text-primary q-mt-md">经办人信息</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.driver_name" label="经办人姓名" :rules="[rules.required]" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.driver_identity_number" label="身份证号" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.driver_telephone_number" label="手机号码" /></div>
                       <div class="col-12">
                           <q-file filled v-model="formData.driver_identity_image_arr" label="身份证图片" multiple accept="image/*">
                               <template v-slot:append>
                                   <q-icon v-if="formData.driver_identity_image_arr" name="close" @click.stop.prevent="formData.driver_identity_image_arr = null" class="cursor-pointer" />
                               </template>
                           </q-file>
                       </div>
                   </div>
                </q-form>
              </q-tab-panel>

              <!-- Tab 3: Cargo & Load -->
              <q-tab-panel name="cargo">
                <div class="text-h6 q-mb-md">货物与载重信息</div>
                <q-form class="q-gutter-md">
                   <div class="text-subtitle2 text-primary">货物详情</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12"><q-input filled v-model="formData.cargo_name" label="货物名称" :rules="[rules.required]" /></div>
                       <div class="col-12"><q-input filled v-model="formData.cargo_desc" type="textarea" label="货物描述" rows="3" /></div>
                   </div>

                   <div class="text-subtitle2 text-primary q-mt-md">重量与尺寸</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6"><q-input filled v-model.number="formData.cargo_weight" type="number" label="货物质量 (吨)" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model.number="formData.total_weight" type="number" label="车货总质量 (吨)" /></div>
                       <div class="col-12"><q-input filled v-model="formData.cargo_size_arr_str" label="货物外廓尺寸 (长,宽,高 米)" hint="以逗号分隔，如: 10,2.5,3" :rules="[rules.sizeArray]" /></div>
                       <div class="col-12"><q-input filled v-model="formData.total_size_arr_str" label="车货总体外廓尺寸 (长,宽,高 米)" hint="以逗号分隔，如: 15,2.5,4" :rules="[rules.sizeArray]" /></div>
                       <div class="col-12">
                           <q-file filled v-model="formData.outline_image_arr" label="车货总体轮廓图" multiple accept="image/*">
                               <template v-slot:append>
                                   <q-icon v-if="formData.outline_image_arr" name="close" @click.stop.prevent="formData.outline_image_arr = null" class="cursor-pointer" />
                               </template>
                           </q-file>
                       </div>
                   </div>
                </q-form>
              </q-tab-panel>

              <!-- Tab 4: Transport Plan -->
              <q-tab-panel name="plan">
                <div class="text-h6 q-mb-md">运输计划</div>
                 <q-form class="q-gutter-md">
                   <div class="text-subtitle2 text-primary">起讫点</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.start_point" label="出发地" /></div>
                       <div class="col-12 col-md-6"><q-input filled v-model="formData.end_point" label="目的地" /></div>
                   </div>

                   <div class="text-subtitle2 text-primary q-mt-md">时间安排</div>
                   <div class="row q-col-gutter-sm">
                       <div class="col-12 col-md-6">
                           <q-input filled v-model="formData.start_date" label="通行开始时间">
                               <template v-slot:append><q-icon name="event" class="cursor-pointer"><q-popup-proxy cover transition-show="scale" transition-hide="scale"><q-date v-model="formData.start_date" mask="YYYY-MM-DD HH:mm"><div class="row items-center justify-end"><q-btn v-close-popup label="Close" color="primary" flat /></div></q-date></q-popup-proxy></q-icon></template>
                           </q-input>
                       </div>
                       <div class="col-12 col-md-6">
                           <q-input filled v-model="formData.end_date" label="通行结束时间">
                               <template v-slot:append><q-icon name="event" class="cursor-pointer"><q-popup-proxy cover transition-show="scale" transition-hide="scale"><q-date v-model="formData.end_date" mask="YYYY-MM-DD HH:mm"><div class="row items-center justify-end"><q-btn v-close-popup label="Close" color="primary" flat /></div></q-date></q-popup-proxy></q-icon></template>
                           </q-input>
                       </div>
                   </div>
                </q-form>
              </q-tab-panel>

            </q-tab-panels>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, reactive, watch } from 'vue'
import { useQuasar } from 'quasar'
import { createApplication, updateApplication } from '../api/application'

const props = defineProps({
  modelValue: Boolean,
  syncSource: {
      type: Object,
      default: () => ({ vehicle: null, route: null })
  },
  initialData: {
      type: Object,
      default: () => null
  }
})

const emit = defineEmits(['update:modelValue', 'save'])
const $q = useQuasar()

const tab = ref('vehicle')
const currentAppId = ref(null) // Track backend ID
const showDialog = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// Reactive form data initialized with empty values
const formData = reactive({
    // Vehicle
    tractor_plate_number: '',
    tractor_model: '',
    tractor_cur_weight: null,
    tractor_owner: '',
    tractor_licence_image_arr: null,
    
    trailer_plate_number: '',
    trailer_model: '',
    trailer_cur_weight: null,
    trailer_owner: '',
    trailer_licence_image_arr: null,
    
    axle_count: null,
    tire_count: null,
    axis_weights_str: '',
    axis_distances_str: '',
    
    // Owner
    entity_name: '',
    entity_license_number: '',
    entity_address: '',
    entity_license_image_arr: null,
    
    driver_name: '',
    driver_identity_number: '',
    driver_telephone_number: '',
    driver_identity_image_arr: null,

    // Cargo
    cargo_name: '',
    cargo_desc: '',
    cargo_weight: null,
    total_weight: null,
    cargo_size_arr_str: '', 
    total_size_arr_str: '', 
    outline_image_arr: null,

    // Plan
    start_point: '',
    end_point: '',
    start_date: '',
    end_date: ''
})

// Sync Logic
const syncFromRoutePlan = () => {
    let syncedCount = 0
    // Sync Vehicle
    if (props.syncSource.vehicle) {
        const v = props.syncSource.vehicle
        formData.axle_count = v.axis_count
        formData.total_weight = v.total_weight
        formData.total_size_arr_str = `${v.length},${v.width},${v.height}`
        // Guess tractor model from name if simple
        if (!formData.tractor_model) formData.tractor_model = v.name
        syncedCount++
    }
    
    // Sync Route
    if (props.syncSource.route) {
        const r = props.syncSource.route
        if (r.origin) formData.start_point = r.origin
        if (r.destination) formData.end_point = r.destination
        if (r.departure_time) formData.start_date = r.departure_time
        syncedCount++
    }
    
    if (syncedCount > 0) {
        $q.notify({
            color: 'positive',
            message: '已同步规划数据',
            icon: 'check'
        })
    } else {
         $q.notify({
            color: 'warning',
            message: '暂无规划数据可同步',
            icon: 'warning'
        })
    }
}


// Load data from localStorage on mount/show
watch(showDialog, (val) => {
    if (val) {
        // Priority 1: initialData prop
        if (props.initialData) {
            Object.assign(formData, props.initialData)
            // If initialData has an ID (loaded from backend elsewhere), set it
            if (props.initialData.id) {
                currentAppId.value = props.initialData.id
            }
            return
        }
        
        // Priority 2: LocalStorage
        const saved = localStorage.getItem('qualification_form_data')
        if (saved) {
            try {
                const parsed = JSON.parse(saved)
                Object.assign(formData, parsed)
                if (parsed.id) currentAppId.value = parsed.id
            } catch (e) {
                console.error('Failed to load saved data', e)
            }
        }
    }
})

// Helper to normalize comma strings (English/Chinese) to array
const parseArrayStr = (str) => {
    if (!str) return []
    return str.replace(/，/g, ',').split(',').map(s => s.trim()).filter(s => s !== '')
}

// Validation Rules
const rules = {
    required: val => !!val || '必填',
    numeric: val => !val || /^\d+(\.\d+)?$/.test(val) || '请输入数字',
    sizeArray: val => {
        if (!val) return true
        const arr = parseArrayStr(val)
        return arr.length === 3 || '格式错误，需包含长、宽、高三个数值 (用逗号分隔)'
    },
    axisWeights: val => {
        if (!val) return true
        const count = formData.axle_count
        if (!count) return '请先填写轴数'
        const arr = parseArrayStr(val)
        return arr.length === count || `轴重数量 (${arr.length}) 与轴数 (${count}) 不一致`
    },
    axisDistances: val => {
        if (!val) return true
        const count = formData.axle_count
        if (!count) return '请先填写轴数'
        const arr = parseArrayStr(val)
        // Spacings should be axle_count - 1
        return arr.length === (count - 1) || `轴距数量 (${arr.length}) 应为轴数-1 (${count - 1})`
    }
}

const transformToPayload = (data) => {
    const formatDate = (dateStr) => {
        if (!dateStr) return null
        try {
            return new Date(dateStr).toISOString()
        } catch (e) {
            console.error("Date parse error", e)
            return null
        }
    }

    return {
        status: "DRAFT",
        vehicle_info: {
            tractor_plate_number: data.tractor_plate_number,
            tractor_model: data.tractor_model,
            tractor_cur_weight: data.tractor_cur_weight,
            tractor_owner: data.tractor_owner,
            
            trailer_plate_number: data.trailer_plate_number,
            trailer_model: data.trailer_model,
            trailer_cur_weight: data.trailer_cur_weight,
            trailer_owner: data.trailer_owner,
            
            axle_count: data.axle_count,
             tire_count: data.tire_count,
             axis_weights: parseArrayStr(data.axis_weights_str).map(Number),
             axis_distances: parseArrayStr(data.axis_distances_str).map(Number)
         },
         owner_info: {
            entity_name: data.entity_name,
            entity_license_number: data.entity_license_number,
            entity_address: data.entity_address,
            
            driver_name: data.driver_name,
            driver_identity_number: data.driver_identity_number,
            driver_telephone_number: data.driver_telephone_number
        },
        cargo_info: {
            cargo_name: data.cargo_name,
            cargo_desc: data.cargo_desc,
            cargo_weight: data.cargo_weight,
            total_weight: data.total_weight,
            cargo_size_arr_str: data.cargo_size_arr_str,
            total_size_arr_str: data.total_size_arr_str
        },
        transport_plan: {
            start_point: data.start_point,
            end_point: data.end_point,
            start_date: formatDate(data.start_date),
            end_date: formatDate(data.end_date)
        }
    }
}

const saveData = async () => {
    // Validate Logic before save
    if (formData.axis_weights_str && rules.axisWeights(formData.axis_weights_str) !== true) {
        $q.notify({ color: 'negative', message: '轴重分布校验失败，请检查输入', icon: 'error' })
        return
    }
    if (formData.axis_distances_str && rules.axisDistances(formData.axis_distances_str) !== true) {
        $q.notify({ color: 'negative', message: '轴距分布校验失败，请检查输入', icon: 'error' })
        return
    }

    // 1. Save to LocalStorage (Legacy/Backup)
    // We also save the ID if we have it
    const localData = { ...formData, id: currentAppId.value }
    localStorage.setItem('qualification_form_data', JSON.stringify(localData))
    
    // 2. Save to Backend
    try {
        const payload = transformToPayload(formData)
        let response
        if (currentAppId.value) {
            response = await updateApplication(currentAppId.value, payload)
            $q.notify({ color: 'positive', message: '已更新云端数据', icon: 'cloud_done' })
        } else {
            response = await createApplication(payload)
            currentAppId.value = response.id
            // Update local storage with new ID
            localData.id = response.id
            localStorage.setItem('qualification_form_data', JSON.stringify(localData))
            
            $q.notify({ color: 'positive', message: '已创建云端数据', icon: 'cloud_upload' })
        }
    } catch (e) {
        console.error('Failed to save to cloud', e)
        $q.notify({ color: 'warning', message: '云端同步失败，仅保存本地', icon: 'cloud_off' })
    }

    emit('save', { ...formData, id: currentAppId.value })
}
</script>
