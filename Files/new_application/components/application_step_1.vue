<template>
	<view class="uni-container">
		<!-- 步骤1: 基础信息填写 -->
		<h3 class="text-xl font-semibold mb-6">基础信息填写</h3>

		<!-- 页签 -->
		<view class="mb-6">
			<view class="flex border-b">
				<view class="tab-bar">
					<view class="tab-item" @click="switchTab('template')"
						:class="{ active: this.activeTab === 'template' }">
						使用模板
					</view>
					<view class="tab-item" @click="switchTab('manual')"
						:class="{ active: this.activeTab === 'manual' }">
						手动输入
					</view>
				</view>
			</view>
		</view>

		<!-- 历史模板选项卡 -->
		<view id="template-content" class="mt-4" v-if="this.activeTab === 'template'">
			<view class="form-group mb-4">
				<label class="block text-gray-700 mb-2">选择历史模板</label>
				<uni-data-picker v-model="formData.vehicle_template_id" collection="dd-vehicle-template"
					field="_id as value, name as text" :where="`user_id == '${this.loginUid}'`"
					@change="onTemplateChange"></uni-data-picker>
			</view>
		</view>

		<!-- 手动输入选项卡 -->
		<view id="guided-content" class="mt-4" v-if="this.activeTab === 'manual'">
			<view class="info-notice bg-blue-50 p-4 rounded-md mb-4">
				<p class="text-blue-800">
					<i class="fas fa-info-circle mr-2"></i>
					请填写以下业户、经办人、牵引车和挂车信息。
				</p>
			</view>
			<view class="form-container">
				<uni-forms ref="form" :model="formData" :rules="rules" validateTrigger="bind" class="wide-form"
					style="max-width: 1000px; padding: 0px;" label-position="top" label-width="100%">
					<!-- 基础信息区块 -->
					<view class="form-section">
						<view class="section-title">基础信息</view>
						<view class="form-row">
							<uni-forms-item name="name" label="模板名称" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.name" trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="axle_count" label="轴数" required class="form-item">
								<uni-easyinput placeholder="请输入轴数" type="number" v-model.number="formData.axle_count"
									@change="handleAxleCountChange"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="tire_count" label="轮胎数" required class="form-item">
								<uni-easyinput placeholder="请输入" type="number"
									v-model="formData.tire_count"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row" v-if="formData.axle_count > 0">
							<uni-forms-item label="轴距（单位：米）" required class="form-item"
								style="margin-bottom: 0px;"></uni-forms-item>
							<view class="axle-item-container">
								<view class="axle-item" v-for="(distance, index) in formData.axle_distance_arr"
									:key="index" v-if="formData.axle_count > 1">
									<uni-forms-item :name="'axle_distance_arr['+index+']'" :rules="min0_decimal2_rules"
										style="margin-bottom: 0px;">
										<uni-easyinput type="number" placeholder="请输入"
											v-model.number="formData.axle_distance_arr[index]"></uni-easyinput>
									</uni-forms-item>
								</view>
							</view>
						</view>
					</view>

					<!-- 业户信息区块 -->
					<view class="form-section">
						<view class="section-title">业户信息</view>
						<view class="form-row">
							<uni-forms-item name="entity_name" label="业户名称" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.entity_name"
									trim="both"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="entity_license_number" label="道路运输经营许可证号" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.entity_license_number"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="entity_address" label="地址" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.entity_address"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="entity_license_start_date" label="许可证有效期-起始日期" required
								class="form-item">
								<uni-datetime-picker return-type="timestamp" type="date"
									v-model="formData.entity_license_start_date"></uni-datetime-picker>
							</uni-forms-item>
							<uni-forms-item name="entity_license_end_date" label="许可证有效期-终止日期" required
								class="form-item">
								<uni-datetime-picker return-type="timestamp" type="date"
									v-model="formData.entity_license_end_date"></uni-datetime-picker>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="entity_license_image_arr" label="道路运输经营许可证图片" required class="form-item">
								<uni-file-picker file-mediatype="image" :limit="3" :image-styles="imageStyles"
									v-model="formData.entity_license_image_arr"></uni-file-picker>
							</uni-forms-item>
						</view>
					</view>

					<!-- 经办人信息 -->
					<view class="form-section">
						<view class="section-title">经办人信息</view>
						<view class="form-row">
							<uni-forms-item name="driver_name" label="经办人姓名" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.driver_name"
									trim="both"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="driver_identity_number" label="经办人身份证" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.driver_identity_number"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="driver_telephone_number" label="手机号码" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.driver_telephone_number"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="driver_identity_image_arr" label="身份证" required class="form-item">
								<uni-file-picker file-mediatype="image" :limit="2" :image-styles="imageStyles"
									v-model="formData.driver_identity_image_arr"></uni-file-picker>
							</uni-forms-item>
						</view>
					</view>

					<!-- 牵引车信息 -->
					<view class="form-section">
						<view class="section-title">牵引车或运输车辆信息</view>
						<view class="form-row">
							<uni-forms-item name="tractor_plate_number" label="车辆牌号" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.tractor_plate_number"
									trim="both"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="tractor_model" label="厂牌型号" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.tractor_model"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="tractor_cur_weight" label="整备质量（单位：吨）" required class="form-item">
								<uni-easyinput placeholder="请输入，保留小数点后两位" type="number"
									v-model="formData.tractor_cur_weight"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="tractor_owner" label="所有人" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.tractor_owner"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="tractor_licence_image_arr" label="车辆行驶证" required class="form-item">
								<uni-file-picker file-mediatype="image" :limit="2" :image-styles="imageStyles"
									v-model="formData.tractor_licence_image_arr"></uni-file-picker>
							</uni-forms-item>
						</view>
					</view>

					<!-- 挂车信息 -->
					<view class="form-section">
						<view class="section-title">挂车信息</view>
						<view class="form-row">
							<uni-forms-item name="trailer_plate_number" label="挂车牌号" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.trailer_plate_number"
									trim="both"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="trailer_model" label="厂牌型号" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.trailer_model"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="trailer_cur_weight" label="整备质量（单位：吨）" required class="form-item">
								<uni-easyinput placeholder="请输入，保留小数点后两位" type="number"
									v-model="formData.trailer_cur_weight"></uni-easyinput>
							</uni-forms-item>
							<uni-forms-item name="trailer_owner" label="挂车所有人" required class="form-item">
								<uni-easyinput placeholder="请输入" v-model="formData.trailer_owner"
									trim="both"></uni-easyinput>
							</uni-forms-item>
						</view>
						<view class="form-row">
							<uni-forms-item name="trailer_licence_image_arr" label="挂车车辆行驶证" required class="form-item">
								<uni-file-picker file-mediatype="image" :limit="2" :image-styles="imageStyles"
									v-model="formData.trailer_licence_image_arr"></uni-file-picker>
							</uni-forms-item>
						</view>
					</view>

					<!-- 按钮 -->
					<view class="uni-group">
						<button class="uni-button" type="primary" size="mini" style="width: 120px;"
							@click="onClickSaveBtn" v-if="this.buttonStatus.save">保存到当前模板</button>
						<button class="uni-button" type="primary" size="mini" style="width: 120px;"
							@click="onClickAddBtn" v-if="this.buttonStatus.add">保存为新模板</button>
						<button class="uni-button" type="primary" size="mini" style="width: 120px;"
							@click="onClickNextBtn" v-if="this.buttonStatus.next">下一步</button>
					</view>
				</uni-forms>
			</view>
		</view>
	</view>
</template>

<script>
	import {
		validator
	} from '../../../js_sdk/validator/dd-vehicle-template.js';
	import {
		min0_decimal2_rules
	} from '../../../js_sdk/validator/dd-common-validator.js';

	const FORM_INIT_TEMPLATE = {
		"vehicle_template_id": "",
		"name": "",
		"tire_count": 0,
		"axle_count": 0,
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
		"trailer_licence_image_arr": null
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
			// 按钮状态
			let buttonStatus = {
				"save": false,
				"add": true,
				"next": false
			}
			// 图片回显样式
			let imageStyles = {
				width: 128,
				height: 128
			}
			return {
				dd_vehicle_template_co: null, // 车辆模板云对象
				loginUid: "", // 登录用户id
				activeTab: "template", // 当前选中的页签，template选择模板，manual手动输入
				formData, // 表单数据
				buttonStatus, // 按钮状态
				imageStyles, // 图片回显样式
				rules: {
					...getValidator(Object.keys(formData)), // 表单验证规则
				},
				min0_decimal2_rules, // 大于0的两位小数验证规则
				formWatchHandler: null // 表单监听对象
			}
		},

		created() {
			this.dd_vehicle_template_co = uniCloud.importObject("dd-vehicle-template-co");
			this.loginUid = uniCloud.getCurrentUserInfo().uid;
			this.formData.vehicle_template_id = this.applFormData.vehicle_template_id; // 读取父组件缓存
			this.onTemplateChange();
			this.openFormWatch();
		},

		methods: {
			/**
			 * 处理轴数变化，动态生成对应数量的轴距输入框
			 * @param {Object} value 轴数
			 */
			handleAxleCountChange(value) {
				// 确保轴数是有效的正整数
				const count = parseInt(value, 10) || 0;
				this.formData.axle_count = count > 0 ? count : 0;
				// 调整数组长度
				this.formData.axle_distance_arr = this.formData.axle_distance_arr.slice(0, this.formData.axle_count - 1);
				for (let i = this.formData.axle_distance_arr.length; i < this.formData.axle_count - 1; i++) {
					this.formData.axle_distance_arr.push(null);
				}
			},

			/**
			 * 切换标签页
			 * @param {Object} tab 标签
			 */
			switchTab(tab) {
				this.activeTab = tab;
			},

			/**
			 * 模板选择变化
			 */
			async onTemplateChange() {
				if (!this.formData.vehicle_template_id) {
					this.resetForm();
				} else {
					// 打开加载
					uni.showLoading({
						mask: true
					});
					// 关闭表单监听
					this.closeFormWatch();
					try {
						// 查询模板信息
						let res = await this.dd_vehicle_template_co.getById(this.formData.vehicle_template_id);
						//加载表单信息
						let templateData = res.data[0];
						this.formData = templateData;
						this.formData.vehicle_template_id = templateData._id;
						if (templateData.axle_distance_arr && templateData.axle_distance_arr.length) { // 设置轴数
							this.formData.axle_count = templateData.axle_distance_arr.length + 1;
						}
						// 跳转手动输入页签
						this.switchTab("manual");
						// 数据更新后 DOM 并不会立即更新，下一个事件循环才进行渲染
						this.$nextTick(() => {
							// 确认模板
							this.onConfirmTemplate();
							// 表单数据变更时，需要重新计算
							this.$emit("update-appl-form", {
								need_calculate: true
							});
						});

					} catch (err) {
						uni.showModal({
							content: err.message || '请求服务失败',
							showCancel: false
						})
					} finally {
						this.$nextTick(() => {
							// 关闭加载
							uni.hideLoading();
							// 开启表单监听
							this.openFormWatch();
						});
					}
				}
			},

			/**
			 * 点击保存按钮
			 */
			onClickSaveBtn() {
				this.submit(this.formData.vehicle_template_id);
			},

			/**
			 * 点击新增按钮
			 */
			onClickAddBtn() {
				this.submit();
			},

			/**
			 * 点击下一步按钮
			 */
			onClickNextBtn() {
				// 进入下一步
				this.$emit("nextStep");
			},

			/**
			 * @param {Object} templateId 模板id，为空则新增
			 */
			async submit(templateId) {
				// 打开加载
				uni.showLoading({
					mask: true
				})
				try {
					// 验证表单
					let res = await this.$refs.form.validate();
					// 根据是否传入模板id判断更新or插入
					if (templateId) {
						try {
							res = await this.dd_vehicle_template_co.update(this.formData.vehicle_template_id, res);
							uni.showToast({
								title: '保存成功'
							});
							this.onConfirmTemplate();
						} catch (err) {
							uni.showModal({
								content: err.message || '请求服务失败',
								showCancel: false
							})
						}
					} else {
						try {
							res = await this.dd_vehicle_template_co.add(res);
							uni.showToast({
								title: '保存成功'
							});
							this.formData.vehicle_template_id = res.id; // 新增成功后，更新当前模板id
							this.onConfirmTemplate();
						} catch (err) {
							uni.showModal({
								content: err.message || '请求服务失败',
								showCancel: false
							})
						}
					}
				} catch {
					return;
				} finally {
					//关闭加载
					uni.hideLoading()
				}
			},

			/**
			 * 确认事件
			 */
			onConfirmTemplate() {
				// 将当前模板id传给父组件
				this.$emit("update-appl-form", this.formData);
				// 更改按钮状态
				this.buttonStatus = {
					"save": false,
					"add": false,
					"next": true
				};
				// 开启表单监听
				this.openFormWatch();
			},

			/**
			 * 重置表单
			 */
			resetForm() {
				// 深拷贝重置表单数据
				this.formData = JSON.parse(JSON.stringify(FORM_INIT_TEMPLATE));
				// 重置父组件表单
				this.$emit("update-appl-form", this.formData);
				// 重置关联状态
				this.buttonStatus = {
					"save": false,
					"add": true,
					"next": false
				};
				// 开启表单监听
				this.openFormWatch();
			},

			/**
			 * 开启表单监听
			 */
			openFormWatch() {
				this.closeFormWatch();
				this.formWatchHandler = this.$watch('formData', () => {
					// 表单数据变更时，更改按钮状态
					this.buttonStatus = {
						"save": this.formData.vehicle_template_id ? true : false,
						"add": true,
						"next": false
					};
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
	};
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

	/* 标签页样式 */
	.tab-bar {
		display: flex;
	}

	.tab-item {
		padding: 0.5rem 1rem;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		transition: all 0.2s ease;
	}

	.tab-item.active {
		border-bottom-color: #3b82f6;
		color: #3b82f6;
		font-weight: 500;
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