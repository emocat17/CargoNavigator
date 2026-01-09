<template>
	<view class="uni-container">
		<!-- 步骤2: 运输信息填写 -->
		<h3 class="text-xl font-semibold mb-6">运输信息填写</h3>
		<view class="info-notice bg-blue-50 p-4 rounded-md mb-6">
			<p class="text-blue-800">
				<i class="fas fa-info-circle mr-2"></i>
				请填写以下关键参数，这些参数将用于路线计算和规划。
			</p>
		</view>

		<view class="form-container">
			<uni-forms ref="form" :model="formData" :rules="rules" validateTrigger="bind" class="wide-form"
				style="max-width: 1000px; padding: 0px;" label-position="top" label-width="100%">
				<!-- 基础信息 -->
				<view class="form-section">
					<view class="section-title">基础信息</view>
					<view class="form-row">
						<uni-forms-item name="cargo_name" label="货物名称" required class="form-item">
							<uni-easyinput placeholder="请输入" v-model="formData.cargo_name" trim="both"></uni-easyinput>
						</uni-forms-item>
					</view>
					<view class="form-row">
						<uni-forms-item name="cargo_desc" label="货物描述" class="form-item">
							<uni-easyinput placeholder="请输入" v-model="formData.cargo_desc" type="textarea"
								rows="3"></uni-easyinput>
						</uni-forms-item>
					</view>
					<view class="form-row">
						<uni-forms-item name="cargo_weight" label="货物质量（单位：吨）" required class="form-item">
							<uni-easyinput placeholder="请输入" type="number"
								v-model="formData.cargo_weight"></uni-easyinput>
						</uni-forms-item>
						<uni-forms-item name="total_weight" label="车货总质量（单位：吨）" required class="form-item">
							<uni-easyinput placeholder="请输入" type="number"
								v-model="formData.total_weight"></uni-easyinput>
						</uni-forms-item>
					</view>
					<view class="form-row">
						<uni-forms-item name="cargo_size_arr" label="货物外廓尺寸（单位：米)" required class="form-item">
							<view class="size-input-group">
								<uni-forms-item class="size-input" :name="'cargo_size_arr[0]'"
									:rules="min0_decimal2_rules">
									<uni-easyinput placeholder="长" type="number"
										v-model.number="formData.cargo_size_arr[0]"></uni-easyinput>
								</uni-forms-item>
								<text class="size-separator">×</text>
								<uni-forms-item class="size-input" :name="'cargo_size_arr[1]'"
									:rules="min0_decimal2_rules">
									<uni-easyinput placeholder="宽" type="number"
										v-model.number="formData.cargo_size_arr[1]"></uni-easyinput>
								</uni-forms-item>
								<text class="size-separator">×</text>
								<uni-forms-item class="size-input" :name="'cargo_size_arr[2]'"
									:rules="min0_decimal2_rules">
									<uni-easyinput placeholder="高" type="number"
										v-model.number="formData.cargo_size_arr[2]"></uni-easyinput>
								</uni-forms-item>
							</view>
						</uni-forms-item>
					</view>
					<view class="form-row">
						<uni-forms-item name="total_size_arr" label="车货总体外廓尺寸（单位：米)" required class="form-item">
							<view class="size-input-group">
								<uni-forms-item class="size-input" :name="'total_size_arr[0]'"
									:rules="min0_decimal2_rules">
									<uni-easyinput placeholder="长" type="number"
										v-model.number="formData.total_size_arr[0]"></uni-easyinput>
								</uni-forms-item>
								<text class="size-separator">×</text>
								<uni-forms-item class="size-input" :name="'total_size_arr[1]'"
									:rules="min0_decimal2_rules">
									<uni-easyinput placeholder="宽" type="number"
										v-model.number="formData.total_size_arr[1]"></uni-easyinput>
								</uni-forms-item>
								<text class="size-separator">×</text>
								<uni-forms-item class="size-input" :name="'total_size_arr[2]'"
									:rules="min0_decimal2_rules">
									<uni-easyinput placeholder="高" type="number"
										v-model.number="formData.total_size_arr[2]"></uni-easyinput>
								</uni-forms-item>
							</view>
						</uni-forms-item>
					</view>
					<view class="form-row">
						<uni-forms-item label="轴荷分布（单位：吨）" required class="form-item"
							style="margin-bottom: 0px;"></uni-forms-item>
						<view class="axle-item-container">
							<view class="axle-item" v-for="(weight, index) in formData.axle_weight_arr" :key="index"
								v-if="formData.axle_count > 0">
								<uni-forms-item :name="'axle_weight_arr['+index+']'" :rules="min0_decimal2_rules"
									style="margin-bottom: 0px;">
									<uni-easyinput type="number" placeholder="请输入"
										v-model.number="formData.axle_weight_arr[index]"></uni-easyinput>
								</uni-forms-item>
							</view>
						</view>
					</view>
				</view>

				<!-- 路线信息 -->
				<view class="form-section">
					<view class="section-title">路线信息（目前仅支持福建省内地址）</view>
					<view class="form-row">
						<uni-forms-item name="start_point_city" label="出发地" required class="form-item">
							<uni-data-picker v-model="formData.start_point_city" collection="opendb-city-china"
								field="name as value, name as text"
								:where="`type == 1 && parent_code == '350000'`"></uni-data-picker>
						</uni-forms-item>
						<uni-forms-item name="start_point" label="详细地址" required class="form-item">
							<uni-easyinput placeholder="请输入" v-model="formData.start_point" trim="both"></uni-easyinput>
						</uni-forms-item>
					</view>
					<view class="form-row">
						<uni-forms-item name="end_point_city" label="目的地" required class="form-item">
							<uni-data-picker v-model="formData.end_point_city" collection="opendb-city-china"
								field="name as value, name as text"
								:where="`type == 1 && parent_code == '350000'`"></uni-data-picker>
						</uni-forms-item>
						<uni-forms-item name="end_point" label="详细地址" required class="form-item">
							<uni-easyinput placeholder="请输入" v-model="formData.end_point" trim="both"></uni-easyinput>
						</uni-forms-item>
					</view>
				</view>

				<!-- 通行时间 -->
				<view class="form-section">
					<view class="section-title">通行时间</view>
					<view class="form-row">
						<uni-forms-item name="start_date" label="通行开始时间" required class="form-item">
							<uni-datetime-picker return-type="timestamp" type="date"
								v-model="formData.start_date"></uni-datetime-picker>
						</uni-forms-item>
						<uni-forms-item name="end_date" label="通行结束时间" required class="form-item">
							<uni-datetime-picker return-type="timestamp" type="date"
								v-model="formData.end_date"></uni-datetime-picker>
						</uni-forms-item>
					</view>
				</view>

				<!-- 按钮 -->
				<view class="uni-group">
					<button class="uni-button" type="default" size="mini" style="width: 120px;"
						@click="onClickPrevBtn">上一步</button>
					<button class="uni-button" type="primary" size="mini" style="width: 120px;"
						@click="onClickNextBtn">下一步</button>
				</view>
			</uni-forms>
		</view>
	</view>
</template>

<script>
	import {
		validator
	} from '../../../js_sdk/validator/dd-application.js';

	import {
		min0_decimal2_rules
	} from '../../../js_sdk/validator/dd-common-validator.js';

	const FORM_INIT_TEMPLATE = {
		"cargo_name": "",
		"cargo_desc": "",
		"cargo_weight": null,
		"total_weight": null,
		"cargo_size_arr": [null, null, null], // 长×宽×高
		"total_size_arr": [null, null, null], // 长×宽×高
		"axle_count": 0,
		"axle_weight_arr": [],
		"start_point": "",
		"start_point_city": "",
		"start_province": "",
		"end_point": "",
		"end_point_city": "",
		"start_date": null,
		"end_date": null
	};

	function getValidator(fields) {
		let result = {}
		for (let key in validator) {
			if (fields.includes(key)) {
				result[key] = validator[key]
			}
		}
		return result
	}

	export default {
		props: {
			// 父组件表单数据
			applFormData: {
				type: Object,
				required: true
			}
		},

		data() {
			// 表单数据
			let formData = {
				...FORM_INIT_TEMPLATE
			};

			return {
				opendb_city_china_co: null, // 城市表云对象
				formData, // 表单数据
				rules: {
					...getValidator(Object.keys(formData)), // 表单验证规则
				},
				min0_decimal2_rules // 大于0的两位小数验证规则
			}
		},

		created() {
			this.opendb_city_china_co = uniCloud.importObject("opendb-city-china-co");
			// 从父组件获取已填写的信息
			Object.keys(this.formData).forEach(key => {
				if (this.applFormData.hasOwnProperty(key)) {
					this.formData[key] = this.applFormData[key]
				};
			});
		},
		mounted() {
			this.handleAxleCountChange(this.formData.axle_count);
			this.openFormWatch();
		},

		methods: {
			/**
			 * 处理轴数变化，动态生成对应数量的轴荷输入框
			 * @param {Object} value 轴数
			 */
			handleAxleCountChange(value) {
				// 确保轴数是有效的正整数
				const count = parseInt(value, 10) || 0;
				this.formData.axle_count = count > 0 ? count : 0;
				// 调整数组长度
				this.formData.axle_weight_arr = this.formData.axle_weight_arr.slice(0, this.formData.axle_count);
				for (let i = this.formData.axle_weight_arr.length; i < this.formData.axle_count; i++) {
					this.formData.axle_weight_arr.push(null);
				}
			},

			/**
			 * 点击上一步按钮
			 */
			onClickPrevBtn() {
				this.$emit("prevStep");
			},

			/**
			 * 点击下一步按钮
			 */
			async onClickNextBtn() {
				// 打开加载
				uni.showLoading({
					mask: true
				})
				let res;
				try {
					// 验证表单
					res = await this.$refs.form.validate();
					// 获取省份
					let queryRes = await this.opendb_city_china_co.getProvinceByName(this.formData
						.start_point_city);
					this.formData.start_province = queryRes.data[0].name;
					// 将表单信息传给父组件
					this.$emit("update-appl-form", this.formData);
					// 进入下一步
					this.$emit("nextStep");
				} catch {
					return;
				} finally {
					//关闭加载
					uni.hideLoading();
				}
			},

			/**
			 * 开启表单监听
			 */
			openFormWatch() {
				this.closeFormWatch();
				this.formWatchHandler = this.$watch('formData', () => {
					// 表单数据变更时，需要重新计算
					this.$emit("update-appl-form", {
						need_calculate: true
					});
					// 监听一次即关闭
					this.closeFormWatch();
				}, {
					deep: true,
					immediate: false
				});
			},

			/**
			 * 关闭表单监听
			 */
			closeFormWatch() {
				if (this.formWatchHandler) {
					this.formWatchHandler();
				}
			}
		}
	}
</script>

<style scoped>
	.form-container {
		display: flex;
		justify-content: center;
		box-sizing: border-box;
	}

	.wide-form {
		width: 100%;
	}

	/* 表单区块样式 */
	.form-section {
		margin-bottom: 25px;
		padding: 15px;
		background-color: #f9f9f9;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}

	/* 区块标题样式 */
	.section-title {
		font-size: 16px;
		font-weight: bold;
		color: #333;
		margin-bottom: 15px;
		padding-bottom: 8px;
		border-bottom: 1px solid #eee;
	}

	/* 行容器 - 控制每行最多两个表单项 */
	.form-row {
		display: flex;
		flex-wrap: wrap;
		margin: 0 0px 15px;
	}

	/* 表单项样式 */
	.form-item {
		flex: 1;
		min-width: 150px;
		max-width: 100%;
		padding: 0 8px;
		box-sizing: border-box;
	}

	/* 确保表单项标签不换行 */
	.uni-forms-item__label {
		white-space: nowrap;
		text-overflow: ellipsis;
		overflow: hidden;
		min-width: 100px;
		max-width: 200px;
	}

	/* 尺寸输入组样式 */
	.size-input-group {
		display: flex;
		align-items: center;
		width: 100%;
	}

	.size-input {
		flex: 1;
		margin: 0px;
	}

	.size-separator {
		margin: 0 8px;
		color: #666;
	}

	::v-deep .size-input .uni-forms-item__label {
		display: none;
	}

	/* 车轴相关输入样式 */
	.axle-item-container {
		display: flex;
		width: 100%;
		flex-wrap: wrap;
		padding-left: 8px;
		gap: 8px;
	}

	.axle-item {
		margin-bottom: 15px;
		flex: 0 0 10%;
		box-sizing: border-box;
	}

	::v-deep .axle-item .uni-forms-item__label {
		display: none;
	}

	/* 按钮样式 */
	.uni-button {
		height: 40px;
		line-height: 40px;
		border-radius: 6px;
	}

	/* 信息提示样式 */
	.info-notice {
		background-color: #eff6ff;
		color: #1e40af;
		padding: 1rem;
		border-radius: 0.375rem;
		margin-bottom: 1.5rem;
	}
</style>