<template>
	<view class="uni-container">
		<!-- 步骤4: 生成申请报告 -->
		<h3 class="text-xl font-semibold mb-6">生成申请报告</h3>
		<view class="info-notice bg-blue-50 p-4 rounded-md mb-6">
			<p class="text-blue-800">
				<i class="fas fa-info-circle mr-2"></i>
				系统将根据您提供的车辆、货物信息和选择的路线，自动生成大件运输申请报告，包括运输参数和护送方案。
			</p>
		</view>

		<!-- 报告生成状态 -->
		<view class="section" v-if="showGenerationStatus">
			<ProgressProcessor :steps="processSteps" @onProcessChange="handleProcessChange"
				@onStepIndexChange="handleStepIndexChange" @onProcessFinished="onProcessFinished" ref="progress" />
			<view class="flex items-center justify-between mb-2">
				<view class="flex items-center">
					<view class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></view>
					<span>{{ currentStatusMessage }}</span>
				</view>
				<span>{{ progressWidth }}</span>
			</view>
			<view class="w-full bg-gray-200 rounded-full h-2">
				<view class="bg-blue-600 h-2 rounded-full" :style="{ width: progressWidth }"></view>
			</view>
		</view>

		<!-- 报告预览 -->
		<view id="report-preview" v-if="showReportPreview">
			<view class="flex justify-between items-center mb-4">
				<h4 class="section-title font-medium">申请报告预览</h4>
			</view>
			<view class="panel border rounded-md overflow-hidden shadow-sm transition-all duration-300 hover:shadow-md"
				style="margin-bottom: 10px;">
				<!-- 报告头部 -->
				<view class="p-6 bg-blue-600 text-white">
					<view class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
						<h2 class="text-2xl font-bold">大件运输申请报告</h2>
						<view class="text-right">
							<p class="text-sm">申请编号</p>
							<p id="report-id" class="font-mono">XXXXXXXX</p>
						</view>
					</view>
					<view class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
						<view>
							<p class="text-sm">申请人</p>
							<p class="font-medium">{{this.formData.driver_name}}</p>
						</view>
						<view>
							<p class="text-sm">申请日期</p>
							<p class="font-medium">{{formatDate(Date.now())}}</p>
						</view>
					</view>
				</view>
			</view>

			<!-- 报告内容 -->
			<uni-forms ref="form" :model="formData" :rules="rules" validateTrigger="bind"
				style="max-width: 100%; padding: 0px;">
				<view class="card-container">
					<!-- 基础信息 -->
					<view class="info-block">
						<view class="block-title">基础信息</view>
						<view class="block-content">
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">申请编号（提交申请后生成）:</text>
									<text class="value">XXXXXXXX</text>
								</view>
								<view class="info-item-half">
									<text class="label">货物名称:</text>
									<text class="value">{{ this.formData.cargo_name }}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">通行开始时间:</text>
									<text class="value">{{ formatDate(this.formData.start_date) }}</text>
								</view>
								<view class="info-item-half">
									<text class="label">通行结束时间:</text>
									<text class="value">{{ formatDate(this.formData.end_date) }}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">起运省:</text>
									<text class="value">{{ this.formData.start_province }}</text>
								</view>
								<view class="info-item-half">
									<text class="label">沿线省:</text>
									<text class="value">{{ this.formData.along_provinces }}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">出发地:</text>
									<text
										class="value">{{ this.formData.start_point_city }}-{{this.formData.start_point}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">目的地:</text>
									<text
										class="value">{{ this.formData.end_point_city }}-{{this.formData.end_point}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-full">
									<text class="label">通行路线:</text>
									<view class="value">
										{{ this.formData.route }}
									</view>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-full">
									<text class="label">风险等级:</text>
									<view class="value">
										{{ this.formData.risk_level }}
									</view>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">货物质量:</text>
									<text class="value">{{ this.formData.cargo_weight }}吨</text>
								</view>
								<view class="info-item-half">
									<text class="label">车货总质量:</text>
									<text class="value">{{ this.formData.total_weight }}吨</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">轴数:</text>
									<text class="value">{{ this.formData.axle_count }}</text>
								</view>
								<view class="info-item-half">
									<text class="label">轮胎数:</text>
									<text class="value">{{ this.formData.tire_count }}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">轴距（米）:</text>
									<text
										class="value">{{ formData.axle_distance_arr ? formData.axle_distance_arr.join('-') : '' }}</text>
								</view>
								<view class="info-item-half">
									<text class="label">轴荷分布（吨）:</text>
									<text
										class="value">{{ formData.axle_weight_arr ? formData.axle_weight_arr.join('+') : '' }}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">货物外廓尺寸（长×宽×高）:</text>
									<text
										class="value">{{ this.formData.cargo_size_arr[0] }}×{{ this.formData.cargo_size_arr[1] }}×{{this.formData.cargo_size_arr[2]}}（米）</text>
								</view>
								<view class="info-item-half">
									<text class="label">车货总体外廓尺寸（长×宽×高）:</text>
									<text
										class="value">{{ this.formData.total_size_arr[0] }}×{{ this.formData.total_size_arr[1] }}×{{this.formData.total_size_arr[2]}}（米）</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-full">
									<text class="label"><text style="color: red;">*</text>车货总体轮廓图:</text>
									<uni-forms-item name="outline_image_arr">
										<uni-file-picker file-mediatype="image" v-model="formData.outline_image_arr"
											:limit="5" :image-styles="imageStyles"></uni-file-picker>
									</uni-forms-item>

								</view>
							</view>
						</view>
					</view>
					<!-- 业户信息 -->
					<view class="info-block">
						<view class="block-title">业户信息</view>
						<view class="block-content">
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">业户名称:</text>
									<text class="value">{{this.formData.entity_name}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">道路运输经营许可证号:</text>
									<text class="value">{{this.formData.entity_license_number}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">地址:</text>
									<text class="value">{{this.formData.entity_address}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">有效期:</text>
									<text class="value">{{this.formData.entity_name}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-full">
									<text class="label">道路运输经营许可证图片:</text>
									<uni-file-picker file-mediatype="image" v-model="formData.entity_license_image_arr"
										:limit="formData.entity_license_image_arr.length" :image-styles="imageStyles"
										:del-icon="false"></uni-file-picker>
								</view>
							</view>
						</view>
					</view>
					<!-- 经办人信息 -->
					<view class="info-block">
						<view class="block-title">经办人信息</view>
						<view class="block-content">
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">经办人姓名:</text>
									<text class="value">{{this.formData.driver_name}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">经办人身份证:</text>
									<text class="value">{{this.formData.driver_identity_number}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">手机号码:</text>
									<text class="value">{{this.formData.driver_telephone_number}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">身份证:</text>
									<uni-file-picker file-mediatype="image" v-model="formData.driver_identity_image_arr"
										:limit="formData.driver_identity_image_arr.length" :image-styles="imageStyles"
										:del-icon="false"></uni-file-picker>
								</view>
								<view class="info-item-half">
									<text class="label"><text style="color: red;">*</text>授权委托书:</text>
									<uni-forms-item name="authorization_image_arr">
										<uni-file-picker file-mediatype="image"
											v-model="formData.authorization_image_arr" :limit="5"
											:image-styles="imageStyles"></uni-file-picker>
									</uni-forms-item>
								</view>
							</view>
						</view>
					</view>
					<!-- 牵引车或运输车信息 -->
					<view class="info-block">
						<view class="block-title">牵引车或运输车信息</view>
						<view class="block-content">
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">车辆牌号:</text>
									<text class="value">{{this.formData.tractor_plate_number}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">厂牌型号:</text>
									<text class="value">{{this.formData.tractor_model}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">整备质量:</text>
									<text class="value">{{this.formData.tractor_cur_weight}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">所有人:</text>
									<text class="value">{{this.formData.tractor_owner}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-fullss">
									<text class="label">车辆行驶证:</text>
									<uni-file-picker file-mediatype="image" v-model="formData.tractor_licence_image_arr"
										:limit="formData.tractor_licence_image_arr.length" :image-styles="imageStyles"
										:del-icon="false"></uni-file-picker>
								</view>
							</view>
						</view>
					</view>
					<!-- 挂车信息 -->
					<view class="info-block">
						<view class="block-title">挂车信息</view>
						<view class="block-content">
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">挂车牌号:</text>
									<text class="value">{{this.formData.trailer_plate_number}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">挂车厂牌型号:</text>
									<text class="value">{{this.formData.trailer_model}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-half">
									<text class="label">整备质量:</text>
									<text class="value">{{this.formData.trailer_cur_weight}}</text>
								</view>
								<view class="info-item-half">
									<text class="label">挂车所有人:</text>
									<text class="value">{{this.formData.trailer_owner}}</text>
								</view>
							</view>
							<view class="info-row">
								<view class="info-item-full">
									<text class="label">挂车车辆行驶证:</text>
									<uni-file-picker file-mediatype="image" v-model="formData.trailer_licence_image_arr"
										:limit="formData.trailer_licence_image_arr.length" :image-styles="imageStyles"
										:del-icon="false"></uni-file-picker>
								</view>
							</view>
						</view>
					</view>
					<!-- 护送方案信息 -->
					<view class="info-block">
						<view class="block-title">护送方案信息</view>
						<view class="block-content">
							<view class="info-item-half">
								<text class="label"><text style="color: red;">*</text>护送方案:</text>
								<uni-forms-item name="escort_plan_file_arr">
									<uni-file-picker file-mediatype="all" v-model="formData.escort_plan_file_arr"
										:limit="5"></uni-file-picker>
								</uni-forms-item>
							</view>
						</view>
					</view>
				</view>
			</uni-forms>
			<!-- 按钮 -->
			<view class="uni-group" v-if="showBtn">
				<button class="uni-button" type="default" size="mini" style="width: 120px;"
					@click="onClickPrevBtn">上一步</button>
				<button class="uni-button" type="primary" size="mini" style="width: 120px;"
					@click="onClickSubmitBtn">提交</button>
			</view>
		</view>
	</view>
</template>

<script>
	import ProgressProcessor from '../../../components/dd-common/ProgressProcessor';
	import {
		validator
	} from '../../../js_sdk/validator/dd-application.js';

	function getValidator(fields) {
		let result = {}
		for (let key in validator) {
			if (fields.includes(key)) {
				result[key] = validator[key]
			}
		}
		return result
	}
	// 申请表单模板
	const FORM_INIT_TEMPLATE = {
		"cargo_name": "",
		"cargo_desc": "",
		"start_date": null,
		"end_date": null,
		"start_province": "",
		"along_provinces": "",
		"start_point": "",
		"start_point_city": "",
		"end_point": "",
		"end_point_city": "",
		"route": "",
		"cargo_weight": null,
		"total_weight": null,
		"axle_count": 0,
		"tire_count": 0,
		"axle_distance_arr": [],
		"axle_weight_arr": [],
		"cargo_size_arr": [null, null, null], // 长×宽×高
		"total_size_arr": [null, null, null], // 长×宽×高
		"outline_image_arr": null,
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
		"authorization_image_arr": null,
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
		"escort_plan_file_arr": null,
		"min_effect_ratio": null,
		"risk_level": "",
	};

	export default {
		props: {
			// 父组件表单数据
			applFormData: {
				type: Object,
				required: true
			}
		},

		components: {
			ProgressProcessor
		},

		data() {
			// 表单数据
			let formData = {
				...FORM_INIT_TEMPLATE
			};
			// 图片回显样式
			let imageStyles = {
				width: 128,
				height: 128
			}
			return {
				// 处理流程步骤数组，展示用
				processSteps: [{
						message: "正在生成运输参数...",
						totalTimeRangeMs: { // 步骤时长
							min: 500,
							max: 500
						},
						intervalRangeMs: { // 完成后到下一个步骤的停顿时间
							min: 0,
							max: 0
						}
					},
					{
						message: "正在制定护送方案...",
						totalTimeRangeMs: {
							min: 500,
							max: 500
						},
						intervalRangeMs: {
							min: 0,
							max: 0
						}
					},
					{
						message: "正在生成路线评估结果...",
						totalTimeRangeMs: {
							min: 600,
							max: 600
						},
						intervalRangeMs: {
							min: 0,
							max: 0
						}
					},
					{
						message: "正在生成报告文档...",
						totalTimeRangeMs: {
							min: 700,
							max: 700
						},
						intervalRangeMs: {
							min: 1000,
							max: 1000
						}
					}
				],
				processShowParams: {
					currentIndex: 0,
					currentPercent: 0
				},

				// 图片回显样式
				imageStyles,

				// 云对象
				dd_application_co: null,
				dd_common_co: null,
				// 表单数据
				formData,
				rules: {
					...getValidator(Object.keys(formData))
				},

				// 状态控制
				showGenerationStatus: true,
				showReportPreview: false,
			};
		},

		computed: {
			currentStatusMessage() {
				if (this.processShowParams.currentPercent >= 100)
					return "报告预览生成完成，即将展示";
				return this.processSteps[this.processShowParams.currentIndex].message;
			},
			progressWidth() {
				const percent = Math.min(this.processShowParams.currentPercent, 100);
				return `${percent.toFixed(2)}%`;
			}
		},

		created() {
			this.dd_application_co = uniCloud.importObject("dd-application-co");
			this.dd_common_co = uniCloud.importObject("dd-common-co");
			// 从父组件获取已填写的信息
			Object.keys(this.formData).forEach(key => {
				if (this.applFormData.hasOwnProperty(key)) {
					this.formData[key] = this.applFormData[key]
				};
			});
		},
		mounted() {
			// 模拟报告生成处理
			this.$refs.progress.start();
		},

		methods: {
			formatDate(timestamp) {
				const date = new Date(timestamp);
				const year = date.getFullYear();
				const month = String(date.getMonth() + 1).padStart(2, '0');
				const day = String(date.getDate()).padStart(2, '0');
				return `${year}-${month}-${day}`;
			},
			handleProcessChange(process) {
				this.processShowParams.currentPercent = process;
			},
			handleStepIndexChange(stepIndex) {
				this.processShowParams.currentIndex = stepIndex;
			},
			onProcessFinished() {
				this.showGenerationStatus = false;
				this.showReportPreview = true;
				this.showBtn = true;
			},

			/**
			 * 点击上一步按钮
			 */
			onClickPrevBtn() {
				this.$emit("prevStep");
			},

			/**
			 * 点击提交
			 */
			onClickSubmitBtn() {
				this.submit();
			},

			async submit() {
				// 验证表单
				let res = await this.$refs.form.validate();
				uni.showModal({
					title: '提交确认',
					content: '确认提交表单',
					success: (res) => {
						if (res.confirm) {
							try {
								uni.showLoading({
									mask: true
								});
								this.dd_application_co.add(this.formData).then((res) => {
									uni.showToast({
										title: '提交成功'
									});
									uni.navigateTo({
										url: '/pages/history/document/index'
									});
								});
							} catch (err) {
								uni.showModal({
									content: err.message || '请求服务失败',
									showCancel: false
								});
							} finally {
								uni.hideLoading()
							}
						}
					}
				});
			}
		}
	};
</script>

<style scoped>
	.container {
		padding: 16px;
		background-color: #f5f5f5;
		min-height: 100vh;
	}

	/* 区块样式 */
	.section {
		margin-bottom: 25px;
		padding: 15px;
		background-color: #f9f9f9;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	/* 区块标题样式 */
	.section-title {
		font-size: 1.125rem;
		font-weight: 500;
		color: #1f2937;
		margin-bottom: 15px;
		padding-bottom: 8px;
		border-bottom: 1px solid #eee;
		width: 100%;
	}

	/* 信息提示样式 */
	.info-notice {
		background-color: #eff6ff;
		color: #1e40af;
		padding: 1rem;
		border-radius: 0.375rem;
	}

	/* 面板样式 */
	.panel {
		transition: box-shadow 0.3s ease;
	}

	.card-container {
		background-color: #fff;
		border-radius: 10px;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
	}

	.info-block {
		margin-bottom: 15px;
	}

	.block-title {
		background-image: linear-gradient(to bottom, #f0f0f0, #e0e0e0);
		padding: 10px;
		border-radius: 3px;
		font-size: 16px;
	}

	.block-content {
		border-left: 1px solid #ddd;
		border-right: 1px solid #ddd;
		border-bottom: 1px solid #ddd;
		border-bottom-left-radius: 5px;
		border-bottom-right-radius: 5px;
		padding: 15px;
	}

	.info-row {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		margin-bottom: 16px;
	}

	.info-item-half {
		min-width: 150px;
		max-width: 100%;
		width: 50%;
		margin-bottom: 12px;
	}

	.info-item-full {
		width: 100%;
		margin-bottom: 12px;
	}

	.label {
		color: #000000;
		font-size: 14px;
		display: block;
		margin-bottom: 4px;
	}

	.value {
		color: #0000ff;
		font-size: 15px;
		line-height: 1.5;
		word-break: break-all;
	}

	/* 动画效果 */
	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}

		100% {
			transform: rotate(360deg);
		}
	}

	.animate-spin {
		animation: spin 1s linear infinite;
	}
</style>