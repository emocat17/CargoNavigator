<template>
	<view class="min-h-screen bg-gray-50">
		<!-- 顶部导航栏 -->
		<header class="bg-white border-b border-gray-200 shadow-sm">
			<view class="px-4 py-3">
				<h1 class="text-xl font-semibold">新建大件运输申请</h1>
			</view>

			<!-- 步骤指示器 -->
			<view class="shadow-sm p-4">
				<view class="flex items-center justify-between max-w-4xl mx-auto">
					<!-- 步骤1 -->
					<view class="flex items-center">
						<view
							class="flex items-center justify-center w-10 h-10 rounded-full font-bold transition-all duration-300"
							:class="currentStep >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'"
							style="font-size: 16px;">
							1
						</view>
						<span class="ml-2 font-medium transition-colors duration-300"
							:class="currentStep >= 1 ? 'text-blue-600' : 'text-gray-700'">
							基础信息
						</span>
					</view>

					<!-- 连接线1 -->
					<view class="flex-1 h-1 mx-2 transition-colors duration-300"
						:class="currentStep >= 2 ? 'bg-blue-600' : 'bg-gray-200'"></view>

					<!-- 步骤2 -->
					<view class="flex items-center">
						<view
							class="flex items-center justify-center w-10 h-10 rounded-full font-bold transition-all duration-300"
							:class="currentStep >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'"
							style="font-size: 16px;">
							2
						</view>
						<span class="ml-2 font-medium transition-colors duration-300"
							:class="currentStep >= 2 ? 'text-blue-600' : 'text-gray-700'">
							运输信息
						</span>
					</view>

					<!-- 连接线2 -->
					<view class="flex-1 h-1 mx-2 transition-colors duration-300"
						:class="currentStep >= 3 ? 'bg-blue-600' : 'bg-gray-200'"></view>

					<!-- 步骤3 -->
					<view class="flex items-center">
						<view
							class="flex items-center justify-center w-10 h-10 rounded-full font-bold transition-all duration-300"
							:class="currentStep >= 3 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'"
							style="font-size: 16px;">
							3
						</view>
						<span class="ml-2 font-medium transition-colors duration-300"
							:class="currentStep >= 3 ? 'text-blue-600' : 'text-gray-700'">
							路线规划
						</span>
					</view>

					<!-- 连接线3 -->
					<view class="flex-1 h-1 mx-2 transition-colors duration-300"
						:class="currentStep >= 4 ? 'bg-blue-600' : 'bg-gray-200'"></view>

					<!-- 步骤4 -->
					<view class="flex items-center">
						<view
							class="flex items-center justify-center w-10 h-10 rounded-full font-bold transition-all duration-300"
							:class="currentStep >= 4 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'"
							style="font-size: 16px;">
							4
						</view>
						<span class="ml-2 font-medium transition-colors duration-300"
							:class="currentStep >= 4 ? 'text-blue-600' : 'text-gray-700'">
							生成报告
						</span>
					</view>
				</view>

				<!-- 当前步骤提示 -->
				<view class="text-center mt-2 text-sm text-gray-600">
					当前步骤: <span class="font-semibold">{{ currentStep }}</span> / 4
				</view>
			</view>
		</header>

		<!-- 主内容区域 -->
		<main class="container mx-auto px-4 py-8 max-w-4xl">
			<view class="form-container bg-white rounded-lg shadow-sm p-6 transition-all duration-500">
				<!-- 步骤内容区域 -->
				<component :is="currentComponent" @next-step="nextStep" @prev-step="prevStep" @go-to-step="goToStep"
					:appl-form-data="applFormData" @update-appl-form="updateApplForm">
				</component>
			</view>
		</main>

		<!-- 帮助按钮 -->
		<view v-if="showHelpIcon"
		      class="help-button-container fixed bottom-6 right-6"
		      @click.stop="toggleChat">
		  <button class="help-button w-12 h-12 rounded-full bg-blue-500 text-white shadow-lg flex items-center justify-center hover:bg-blue-600 transition-colors duration-300"
		          :aria-pressed="showChat">
		    <i class="fas" :class="showChat ? 'fa-times' : 'fa-robot'"></i>
		  </button>
		</view>

		<!-- H5：遮罩 + iframe（保留你的原结构） -->
		<!-- #ifdef H5 -->
		<view v-show="showChat" class="dify-chat-center" @click.self="closeChat">
		  <view class="dify-chat-card" @click.stop>
		    <iframe :src="chatUrl" class="dify-chat-iframe" frameborder="0" allow="microphone"></iframe>
		  </view>
		</view>
		<!-- #endif -->
	</view>
</template>

<script>
	import page_step_1 from './components/application_step_1.vue'
	import page_step_2 from './components/application_step_2.vue'
	import page_step_3 from './components/application_step_3.vue'
	import page_step_4 from './components/application_step_4.vue'

	// 申请表单模板
	const FORM_INIT_TEMPLATE = {
		// 基础信息
		"vehicle_template_id": "",
		"axle_count": 0,
		"tire_count": 0,
		"axle_distance_arr": [],
		"entity_name": "",
		"entity_license_number": "",
		"entity_address": "",
		"entity_license_start_date": null,
		"entity_license_end_date": null,
		"entity_license_image_arr": null,
		"driver_name": "",
		"driver_identity_number": "",
		"driver_telephone_number": "",
		"driver_identity_image_arr": null,
		"tractor_plate_number": "",
		"tractor_model": "",
		"tractor_cur_weight": null,
		"tractor_owner": "",
		"tractor_licence_image_arr": null,
		"trailer_plate_number": "",
		"trailer_model": "",
		"trailer_cur_weight": null,
		"trailer_owner": "",
		"trailer_licence_image_arr": null,

		// 申请单额外信息
		"cargo_name": "",
		"cargo_desc": "",
		"cargo_weight": null,
		"total_weight": null,
		"cargo_size_arr": [null, null, null], // 长×宽×高
		"total_size_arr": [null, null, null], // 长×宽×高
		"axle_weight_arr": [],
		"outline_image_arr": null,
		"start_point": "",
		"start_point_city": "",
		"end_point": "",
		"end_point_city": "",
		"start_province": "",
		"along_provinces": "",
		"route": "",
		"min_effect_ratio": null,
		"risk_level": "",
		"start_date": null,
		"end_date": null,
		"authorization_image_arr": null,
		"escort_plan_file_arr": null,
		"route_options": [],

		// 状态相关
		"need_calculate": true,
	};

	export default {
		components: {
			page_step_1,
			page_step_2,
			page_step_3,
			page_step_4
		},
		data() {
			// 表单数据
			let applFormData = {
				...FORM_INIT_TEMPLATE
			};

			return {
				currentStep: 1,
				applFormData, // 申请表单数据，由几个步骤共同完成
				showChat: false,
				chatUrl: 'http://103.40.13.100:23452/chatbot/lAJABZGNSYc58Blm',
				showHelpIcon: true
			}
		},
		onLoad(options) {
			//如果有模板ID,加载到表单数据中
			if (options.id) {
				this.applFormData.vehicle_template_id = options.id;
			}
		},
		computed: {
			currentComponent() {
				switch (this.currentStep) {
					case 1:
						return 'page_step_1'
					case 2:
						return 'page_step_2'
					case 3:
						return 'page_step_3'
					case 4:
						return 'page_step_4'
					default:
						return 'page_step_1'
				}
			}
		},
		methods: {
			nextStep() {
				if (this.currentStep < 4) {
					this.currentStep++;
				}
			},
			prevStep() {
				if (this.currentStep > 1) {
					this.currentStep--;
				}
			},
			goToStep(step) {
				this.currentStep = step;
			},

			// 用于接收子组件表单数据更新
			updateApplForm(data) {
				Object.keys(this.applFormData).forEach(key => {
					if (data.hasOwnProperty(key)) {
						this.applFormData[key] = data[key];
					}
				});
				console.log("index.vue update form:", this.applFormData);
			},

			openChat() {
				// #ifdef H5
				console.log('[openChat] open iframe chat');
				this.showChat = true;
				// #endif
			},
			closeChat() {
				// #ifdef H5
				this.showChat = false;
				// #endif
			},
			toggleChat() {
			    if (this.showChat) this.closeChat()
			    else this.openChat()
			  }
		}
	}
</script>

<style scoped>
	/* 表单容器样式 */
	.form-container {
		background-color: #ffffff;
		border-radius: 0.5rem;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
		padding: 1.5rem;
		transition: all 0.5s ease;
	}

	/* 帮助按钮样式 */
	.help-button-container {

		z-index: 99999;
		pointer-events: auto;
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
	}

	.help-button {
		width: 3rem;
		height: 3rem;
		border-radius: 50%;
		background-color: #3b82f6;
		color: #ffffff;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background-color 0.3s ease;
	}

	.help-button:hover {
		background-color: #2563eb;
	}


	.dify-chat-center {
	  position: fixed; inset: 0; background: rgba(0,0,0,.35);
	  display: flex; align-items: center; justify-content: center;
	  z-index: 1100; 
	}
	.dify-chat-card { width: 88vw; max-width: 980px; height: 78vh; background: #fff; border-radius: 12px;
	  box-shadow: 0 6px 24px rgba(0,0,0,.18); overflow: hidden; }
	.dify-chat-iframe { width: 100%; height: 100%; display: block; }
</style>