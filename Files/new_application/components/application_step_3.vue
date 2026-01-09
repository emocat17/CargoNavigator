<template>
	<view class="uni-container">
		<!-- 步骤3: 路线规划与评估 -->
		<h3 class="text-xl font-semibold mb-6">路线规划与评估</h3>
		<view class="info-notice bg-blue-50 p-4 rounded-md mb-6">
			<p class="text-blue-800">
				<i class="fas fa-info-circle mr-2"></i>
				系统将根据您提供的车辆和货物信息，使用高德地图MCP路线规划算法进行路线规划，并计算桥梁效应比值，评估通行可行性。
			</p>
		</view>

		<!-- 处理流程图 -->
		<view class="section">
			<view class="section-title">路线规划处理流程</view>
			<view class="flex items-center justify-between process-flow">
				<!-- 循环渲染流程步骤 -->
				<template v-for="(step, index) in processSteps" :key="index">
					<!-- 步骤内容 -->
					<view class="flex flex-col items-center">
						<view
							class="step-circle w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center mb-2">
							{{ index + 1 }}
						</view>
						<p class="text-sm text-center" style="max-width: 60px;">
							{{ step.title }}
						</p>
					</view>
					<!-- 连接线 -->
					<view class="flex-1 h-1 bg-blue-600 mx-2" v-if="index < processSteps.length - 1"></view>
				</template>
			</view>
		</view>

		<!-- 路线处理状态 -->
		<view class="section" v-if="showProcessingStatus">
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

		<!-- 路线结果 -->
		<view class="section" v-if="showRouteResult">
			<view class="section-title">路线规划结果</view>
			<!-- AI推荐路线 -->
			<view class="mb-6 p-4 bg-blue-50 rounded-md">
				<h5 class="font-medium mb-2">AI推荐路线</h5>
				<view class="flex items-center">
					<i class="fas fa-route text-blue-600 text-xl mr-2"></i>
					<span class="font-medium">路线方案：{{formData.route_options[selectedRouteIndex].path_string}}</span>
				</view>
				<p id="recommendation-reason" class="mt-2 text-sm text-gray-700">
					{{formData.route_options[selectedRouteIndex].recommendation_string}}
				</p>
			</view>
			<!-- 路线选项 -->
			<view class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
				<template v-for="(route, index) in formData.route_options" :key="index">
					<view class="route-option rounded-md p-4 cursor-pointer card-hover"
						:class="selectedRouteIndex === index ? 'border-2 border-blue-200' : 'border border-gray-200'"
						@click="selectRoute(index)">
						<h4 class="font-medium mb-2">路线方案{{ index + 1 }}</h4>
						<view class="flex justify-between">
							<span class="text-sm text-gray-600">最小效应比值</span>
							<span :class="getRiskColorClass(route.risk_level)">
								{{ route.min_effect_ratio }}
							</span>
						</view>
						<view class="flex justify-between">
							<span class="text-sm text-gray-600">风险等级评判</span>
							<span :class="getRiskColorClass(route.risk_level)">
								{{ route.risk_level }}
							</span>
						</view>
					</view>
				</template>
			</view>

			<!-- 地图和桥梁效应分析结果 -->
			<view class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- 地图 -->
				<view class="border rounded-md overflow-hidden">
					<view class="panel-header p-3 bg-gray-100 border-b">
						<h4 class="font-medium">路线地图</h4>
					</view>
					<view class="panel-content h-64 bg-gray-200 flex items-center justify-center">
						<map style="width: 100%; height: 100%;" :latitude="mapConfig.latitude"
							:longitude="mapConfig.longitude" :polyline="mapConfig.polyline" :scale="mapConfig.scale"
							:markers="mapConfig.covers">
						</map>
					</view>
				</view>
				<!-- 桥梁效应分析结果 -->
				<view class="border rounded-md overflow-hidden">
					<view class="panel-header p-3 bg-gray-100 border-b">
						<h4 class="font-medium">桥梁效应分析结果</h4>
					</view>
					<view class="panel-content p-4">
						<view class="mb-4">
							<h5 class="font-medium mb-2">桥梁效应比值数据</h5>
							<view class="space-y-2">
								<view>
									<view class="flex justify-between mb-1">
										<span class="text-sm">正弯矩效应比值</span>
										<span
											class="text-sm font-medium">{{ formData.route_options[selectedRouteIndex].pos_moment_ratio_range.min }}~{{ formData.route_options[selectedRouteIndex].pos_moment_ratio_range.max }}</span>
									</view>
									<view class="w-full bg-gray-200 rounded-full h-2">
										<view class="h-2 rounded-full"
											:style="getRatioStyle('pos_moment', formData.route_options[selectedRouteIndex].pos_moment_ratio_range.min)">
										</view>
									</view>
								</view>
								<view>
									<view class="flex justify-between mb-1">
										<span class="text-sm">负弯矩效应比值</span>
										<span
											class="text-sm font-medium">{{ formData.route_options[selectedRouteIndex].neg_moment_ratio_range.min }}~{{ formData.route_options[selectedRouteIndex].neg_moment_ratio_range.max }}</span>
									</view>
									<view class="w-full bg-gray-200 rounded-full h-2">
										<view class="h-2 rounded-full"
											:style="getRatioStyle('neg_moment', formData.route_options[selectedRouteIndex].neg_moment_ratio_range.min)">
										</view>
									</view>
								</view>
								<view>
									<view class="flex justify-between mb-1">
										<span class="text-sm">剪力效应比值</span>
										<span
											class="text-sm font-medium">{{ formData.route_options[selectedRouteIndex].shear_ratio_range.min }}~{{ formData.route_options[selectedRouteIndex].shear_ratio_range.max }}</span>
									</view>
									<view class="w-full bg-gray-200 rounded-full h-2">
										<view class="h-2 rounded-full"
											:style="getRatioStyle('shear', formData.route_options[selectedRouteIndex].shear_ratio_range.min)">
										</view>
									</view>
								</view>
							</view>
						</view>
						<!-- 通行建议 -->
						<view>
							<h5 class="font-medium mb-2">通行建议</h5>
							<view class="p-3 bg-green-50 rounded-md">
								<p class="text-sm text-green-800">
									<i class="fas fa-check-circle mr-1"></i>
									根据桥梁效应分析结果，所选路线的效应比值均在安全范围内，建议通行。请严格按照大件运输管理规定，在指定时间和路线上通行。
								</p>
							</view>
						</view>
					</view>
				</view>
			</view>
		</view>

		<!-- 按钮 -->
		<view class="uni-group">
			<button class="uni-button" type="default" size="mini" style="width: 120px;"
				@click="onClickPrevBtn">上一步</button>
			<button class="uni-button" type="primary" size="mini" style="width: 120px;"
				@click="onClickNextBtn">下一步</button>
		</view>

	</view>
</template>

<script>
	import ProgressProcessor from '../../../components/dd-common/ProgressProcessor';

	const FORM_INIT_TEMPLATE = {
		"route_options": [],
		"along_provinces": "",
		"route": "",
		"min_effect_ratio": null,
		"risk_level": ""
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

			return {
				// 处理流程步骤数组，展示用
				processSteps: [{
						title: "分析车辆货物信息",
						message: "正在分析车辆参数和货物信息...",
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
						title: "获取本地桩号信息",
						message: "正在获取本地桩号信息...",
						totalTimeRangeMs: {
							min: 800,
							max: 1000
						},
						intervalRangeMs: {
							min: 0,
							max: 0
						}
					}, {
						title: "初始化路线规划",
						message: "正在初始化高德地图MCP路线规划算法...",
						totalTimeRangeMs: {
							min: 1200,
							max: 1500
						},
						intervalRangeMs: {
							min: 0,
							max: 0
						}
					},
					{
						title: "计算桥梁效应比值",
						message: "正在计算桥梁效应比值...",
						totalTimeRangeMs: {
							min: 1200,
							max: 1500
						},
						intervalRangeMs: {
							min: 0,
							max: 0
						}
					},
					{
						title: "评估通行可行性",
						message: "正在评估通行可行性...",
						totalTimeRangeMs: {
							min: 1500,
							max: 2000
						},
						intervalRangeMs: {
							min: 0,
							max: 0
						}
					},
					{
						title: "计算候选路线方案",
						message: "正在计算候选路线...",
						totalTimeRangeMs: {
							min: 1500,
							max: 2000
						},
						intervalRangeMs: {
							min: 1000,
							max: 1000
						},
						canProceed: () => this.routeRetFlag
					}
				],
				processShowParams: {
					currentIndex: 0,
					currentPercent: 0
				},

				// 路线方案相关
				dd_route_co: null,
				dd_common_co: null,
				selectedRouteIndex: -1,
				mapConfig: {
					latitude: 0,
					longitude: 0,
					scale: 10,
					covers: [],
					polyline: [{
						points: [],
						color: "#31c27c",
						width: 6,
						arrowLine: true
					}]
				},

				// 状态控制
				routeRetFlag: false, // 路线方案请求状态
				showProcessingStatus: true,
				showRouteResult: false,
				showBtn: false,

				// 表单数据
				formData
			};
		},

		computed: {
			currentStatusMessage() {
				if (this.processShowParams.currentPercent >= 100)
					return "规划完成，即将展示路线方案";
				return this.processSteps[this.processShowParams.currentIndex].message;
			},
			progressWidth() {
				const percent = Math.min(this.processShowParams.currentPercent, 100);
				return `${percent.toFixed(2)}%`;
			}
		},

		created() {
			this.dd_route_co = uniCloud.importObject("dd-route-co");
			this.dd_common_co = uniCloud.importObject("dd-common-co");
		},
		mounted() {
			if (this.applFormData.need_calculate) {
				// 模拟路线规划加载过程
				this.$refs.progress.start();
				// 请求路线方案
				this.dd_route_co.findAndEvaluateRoutes({
					start_point: this.applFormData.start_point,
					end_point: this.applFormData.end_point,
					axle_weight_arr: this.applFormData.axle_weight_arr,
					axle_distance_arr: this.applFormData.axle_distance_arr
				}).then((res) => {
					this.formData.route_options = res.route_evaluations;
					this.routeRetFlag = true;
					this.$emit("update-appl-form", {
						...this.formData,
						need_calculate: false
					});
				}).catch((err) => {
					uni.showModal({
						content: err.message || '请求服务失败',
						showCancel: false
					})
				});
			} else {
				this.formData.route_options = this.applFormData.route_options;
				this.routeRetFlag = true;
				this.onProcessFinished();
			}
		},

		methods: {
			handleProcessChange(process) {
				this.processShowParams.currentPercent = process;
			},
			handleStepIndexChange(stepIndex) {
				this.processShowParams.currentIndex = stepIndex;
			},
			onProcessFinished() {
				this.selectRoute(0);
				this.showProcessingStatus = false;
				this.showRouteResult = true;
				this.showBtn = true;
			},

			/**
			 * 根据风险等级获取颜色类名
			 * @param {string} riskLevel - 风险等级字符串：高风险、中风险、低风险
			 * @returns {string} - 对应的Tailwind颜色类名
			 */
			getRiskColorClass(riskLevel) {
				switch (riskLevel) {
					case '高风险':
						return 'text-red-600';
					case '中风险':
						return 'text-yellow-600';
					case '低风险':
						return 'text-green-600';
					default:
						return 'text-gray-600'; // 默认灰色
				}
			},

			/**
			 * 计算效应比值比值显示样式样式
			 * @param {Object} type
			 * @param {number} value
			 * @returns {Object} - 包含width和backgroundColor的样式对象
			 */
			getRatioStyle(type, value) {
				// 定义各种效应比值的范围配置
				const ratioConfig = {
					pos_moment: {
						min: 1,
						max: 1.3
					},
					neg_moment: {
						min: 1,
						max: 1.3
					},
					shear: {
						min: 1,
						max: 1.3
					}
				};
				// 颜色配置
				const colorArray = [
					'#dc2626', // bg-red-600
					'#ca8a04', // bg-yellow-600
					'#16a34a', // bg-green-600
				];
				// 获取当前类型的配置
				const config = ratioConfig[type] || ratioConfig.pos_moment;
				// 处理无效值
				if (value === null || value === undefined || isNaN(Number(value))) {
					return {
						width: '0%',
						backgroundColor: colorArray[0] || '#16a34a' // 默认使用第一个颜色
					};
				}
				// 转换为数字
				const numericValue = Number(value);
				// 计算百分比
				const percentage = ((numericValue - config.min) / (config.max - config.min)) * 100;
				// 确保百分比在0-100%之间
				const clampedPercentage = Math.max(0, Math.min(100, percentage));
				// 根据颜色数组长度计算区间
				const colorCount = colorArray.length;
				const interval = 100 / colorCount;
				// 确定使用哪种颜色
				let colorIndex = Math.min(
					Math.floor(clampedPercentage / interval),
					colorCount - 1
				);
				// 处理边界情况
				if (clampedPercentage === 100) {
					colorIndex = colorCount - 1;
				}

				return {
					width: `${clampedPercentage.toFixed(1)}%`,
					backgroundColor: colorArray[colorIndex]
				};
			},

			/**
			 * 选择路线方案
			 * @param {Object} routeIndex 路线在数组中的下标
			 */
			async selectRoute(routeIndex) {
				this.selectedRouteIndex = routeIndex;
				const path_locations = this.formData.route_options[this.selectedRouteIndex].path_locations || [];
				const polyline = this.formData.route_options[this.selectedRouteIndex].polyline || [];
				// 1. 更新路线坐标点
				this.updatePolylinePoints(polyline);
				// 2. 更新标记点（起点、终点、途经点）
				this.updateMarkers(path_locations);
				// 3. 计算并更新地图中心和缩放级别
				this.adjustMapView(path_locations);
				// 更新表单
				this.formData.along_provinces = this.formData.route_options[this.selectedRouteIndex].route_provinces;
				this.formData.route = this.formData.route_options[this.selectedRouteIndex].path_string_details;
				this.formData.min_effect_ratio = this.formData.route_options[this.selectedRouteIndex].min_effect_ratio;
				this.formData.risk_level = this.formData.route_options[this.selectedRouteIndex].risk_level;
			},

			/**
			 * 更新路线坐标点
			 * @param {Object} locations
			 */
			updatePolylinePoints(polyline) {
				this.mapConfig.polyline[0].points = polyline;
			},

			/**
			 * 更新标记点
			 * @param {Object} locations
			 */
			updateMarkers(locations) {
				this.mapConfig.covers = locations.map((item, index) => ({
					latitude: item.location[1],
					longitude: item.location[0],
					iconPath: index === 0 ? "/static/start_point.png" : // 起点图标
						index === locations.length - 1 ? "/static/end_point.png" : // 终点图标
						"/static/waypoints.png", // 途经点图标
					width: 30,
					height: 30,
					title: item.junction // 点击时显示枢纽点名称
				}));
			},

			/**
			 * 调整地图视野（中心坐标和缩放级别）
			 * @param {Object} locations
			 */
			adjustMapView(locations) {
				if (locations.length < 1) return;

				// 提取所有经纬度
				const coords = locations.map(item => ({
					lng: item.location[0],
					lat: item.location[1]
				}));

				// 计算经纬度极值（用于确定视野范围）
				const minLng = Math.min(...coords.map(c => c.lng));
				const maxLng = Math.max(...coords.map(c => c.lng));
				const minLat = Math.min(...coords.map(c => c.lat));
				const maxLat = Math.max(...coords.map(c => c.lat));

				// 计算中心经纬度
				this.mapConfig.longitude = (minLng + maxLng) / 2;
				this.mapConfig.latitude = (minLat + maxLat) / 2;

				// 根据路线跨度自动计算合适的缩放级别
				const newScale = this.calculateScale(minLng, maxLng, minLat, maxLat);
				this.mapConfig.scale = newScale - 0.01;
				this.$nextTick(() => { // 确保缩放刷新
					this.mapConfig.scale = newScale;
				});
			},

			/**
			 * 根据经纬度跨度计算缩放级别
			 * @param {Object} minLng
			 * @param {Object} maxLng
			 * @param {Object} minLat
			 * @param {Object} maxLat
			 */
			calculateScale(minLng, maxLng, minLat, maxLat) {
				// 计算经度和纬度的跨度
				const lngDiff = maxLng - minLng;
				const latDiff = maxLat - minLat;
				const maxDiff = Math.max(lngDiff, latDiff);
				// 缩放级别
				if (maxDiff < 0.01) return 16;
				if (maxDiff < 0.05) return 14;
				if (maxDiff < 0.1) return 13;
				if (maxDiff < 0.5) return 11;
				if (maxDiff < 1) return 10;
				if (maxDiff < 2) return 8;
				if (maxDiff < 5) return 7;
				if (maxDiff < 10) return 6;
				return 5;
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
			onClickNextBtn() {
				this.$emit("update-appl-form", this.formData);
				this.$emit("nextStep");
			},
		}
	};
</script>

<style scoped>
	/* 基础样式和变量 */
	:root {
		--primary-color: #3b82f6;
		--primary-hover: #2563eb;
		--secondary-color: #e5e7eb;
		--secondary-hover: #d1d5db;
		--light-blue-bg: #eff6ff;
		--light-green-bg: #f0fdf4;
		--shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.1);
		--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
		--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
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
	}

	/* 可复用组件样式 */
	.card {
		background-color: #fff;
		border-radius: 8px;
		box-shadow: var(--shadow-sm);
		padding: 1.5rem;
	}

	.card-hover {
		transition: all 0.3s ease;
	}

	.card-hover:hover {
		transform: translateY(-3px);
		box-shadow: var(--shadow-md);
	}

	/* 信息提示样式 */
	.info-notice {
		background-color: #eff6ff;
		color: #1e40af;
		padding: 1rem;
		border-radius: 0.375rem;
		margin-bottom: 1.5rem;
	}

	/* 处理状态样式 */
	.processing-status {
		transition: all 0.3s ease;
	}

	/* 流程步骤样式 */
	.process-flow {
		transition: all 0.3s ease;
	}

	.step-circle {
		transition: transform 0.3s ease;
	}

	.step-circle:hover {
		transform: scale(1.1);
	}

	/* 面板样式 */
	.panel-header {
		font-weight: 500;
	}

	.panel-content {
		transition: background-color 0.3s ease;
	}

	/* 路线选项卡片样式 */
	.route-option {
		transition: all 0.3s ease;
	}

	.route-option:hover {
		border-color: #93c5fd !important;
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

	/* 响应式设计 */
	@media (max-width: 768px) {
		.process-flow {
			overflow-x: auto;
			padding-bottom: 1rem;
		}

		.process-flow>div {
			min-width: 600px;
		}
	}
</style>