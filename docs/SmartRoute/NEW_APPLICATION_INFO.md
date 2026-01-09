# 大件运输申请信息收集规范

本文档整理自 `d:\GitWorks\CargoNavigator\Files\new_application\` 下的业务流程组件，旨在规范大件运输通行资质判断所需的信息收集内容。

## 1. 车辆与设备配置 (Vehicle & Equipment)

用于评估运输工具的物理属性和合法性。

| 字段名称 | 字段标识 (Key) | 类型 | 说明 | 来源组件 |
| :--- | :--- | :--- | :--- | :--- |
| **牵引车/运输车信息** | | | | |
| 车辆牌号 | `tractor_plate_number` | String | | Step 1 |
| 厂牌型号 | `tractor_model` | String | | Step 1 |
| 整备质量 | `tractor_cur_weight` | Number | 单位：吨，保留两位小数 | Step 1 |
| 所有人 | `tractor_owner` | String | | Step 1 |
| 车辆行驶证 | `tractor_licence_image_arr` | Array<Image> | 图片附件 | Step 1 |
| **挂车信息** | | | | |
| 挂车牌号 | `trailer_plate_number` | String | | Step 1 |
| 厂牌型号 | `trailer_model` | String | | Step 1 |
| 整备质量 | `trailer_cur_weight` | Number | 单位：吨，保留两位小数 | Step 1 |
| 挂车所有人 | `trailer_owner` | String | | Step 1 |
| 挂车行驶证 | `trailer_licence_image_arr` | Array<Image> | 图片附件 | Step 1 |
| **轴胎规格** | | | | |
| 轴数 | `axle_count` | Number | | Step 1 |
| 轮胎数 | `tire_count` | Number | | Step 1 |
| 轴距 | `axle_distance_arr` | Array<Number> | 单位：米，数组长度为轴数-1 | Step 1 |

## 2. 业户与经办人信息 (Owner & Handler)

用于确认申请主体资质和联系人信息。

| 字段名称 | 字段标识 (Key) | 类型 | 说明 | 来源组件 |
| :--- | :--- | :--- | :--- | :--- |
| **业户信息** | | | | |
| 业户名称 | `entity_name` | String | | Step 1 |
| 经营许可证号 | `entity_license_number` | String | 道路运输经营许可证号 | Step 1 |
| 地址 | `entity_address` | String | | Step 1 |
| 许可证有效期 | `entity_license_start_date` 至 `entity_license_end_date` | Timestamp | | Step 1 |
| 许可证图片 | `entity_license_image_arr` | Array<Image> | | Step 1 |
| **经办人信息** | | | | |
| 经办人姓名 | `driver_name` | String | | Step 1 |
| 身份证号 | `driver_identity_number` | String | | Step 1 |
| 手机号码 | `driver_telephone_number` | String | | Step 1 |
| 身份证图片 | `driver_identity_image_arr` | Array<Image> | | Step 1 |

## 3. 货物与载重信息 (Cargo & Load)

核心参数，直接影响桥梁效应分析和路线选择。

| 字段名称 | 字段标识 (Key) | 类型 | 说明 | 来源组件 |
| :--- | :--- | :--- | :--- | :--- |
| **货物详情** | | | | |
| 货物名称 | `cargo_name` | String | | Step 2 |
| 货物描述 | `cargo_desc` | String | | Step 2 |
| **重量参数** | | | | |
| 货物质量 | `cargo_weight` | Number | 单位：吨 | Step 2 |
| 车货总质量 | `total_weight` | Number | 单位：吨 | Step 2 |
| 轴荷分布 | `axle_weight_arr` | Array<Number> | 单位：吨，数组长度等于轴数 | Step 2 |
| **尺寸参数** | | | | |
| 货物外廓尺寸 | `cargo_size_arr` | Array<Number> | [长, 宽, 高] 单位：米 | Step 2 |
| 车货总体外廓尺寸 | `total_size_arr` | Array<Number> | [长, 宽, 高] 单位：米 | Step 2 |
| 车货总体轮廓图 | `outline_image_arr` | Array<Image> | 图片附件 | Step 4 |

## 4. 运输计划 (Transport Plan)

| 字段名称 | 字段标识 (Key) | 类型 | 说明 | 来源组件 |
| :--- | :--- | :--- | :--- | :--- |
| **起讫点** | | | | |
| 出发地 | `start_point_city` + `start_point` | String | 城市 + 详细地址 | Step 2 |
| 目的地 | `end_point_city` + `end_point` | String | 城市 + 详细地址 | Step 2 |
| **时间安排** | | | | |
| 通行开始时间 | `start_date` | Timestamp | | Step 2 |
| 通行结束时间 | `end_date` | Timestamp | | Step 2 |

## 5. 系统集成与模块设计 (Module Design)

基于 "独立模块" 的设计原则，本功能将作为一个独立的弹出式模块集成到现有系统中，保持主界面简洁。

### 5.1 入口设计
- **位置**: `RouteForm.vue` 组件中，位于 "车辆配置" 卡片下方。
- **形式**: 添加一个 "通行资质预审信息" 的功能区，提供 "填写/管理" 按钮。
- **交互**: 点击按钮弹出全屏或宽屏 Dialog (`QualificationManager.vue`)。

### 5.2 组件架构 (`QualificationManager.vue`)
采用分步表单 (Stepper) 或 标签页 (Tabs) 结构组织复杂信息。

```mermaid
graph TD
    A[RouteForm Entry] -->|Click| B[QualificationManager Dialog]
    B --> C{Tabs/Steps}
    C -->|Tab 1| D[BasicInfo (Vehicle & Owner)]
    C -->|Tab 2| E[CargoInfo (Cargo & Load)]
    C -->|Tab 3| F[RoutePlan (Transport Plan)]
    C -->|Tab 4| G[Preview & Generate]
```

### 5.3 数据存储方案
- **前端存储**: 使用 `localStorage` 或 Pinia 持久化存储暂存用户输入，避免刷新丢失。
- **数据结构**: 统一封装为 `ApplicationFormData` 对象。

### 5.4 开发任务清单
1.  **创建组件**: `src/components/QualificationManager.vue` (已完成)
    -   已实现基于 Tabs 的分步表单结构。
    -   包含：车辆与设备、业户与经办人、货物与载重、运输计划四个核心板块。
    -   数据持久化：采用 `localStorage` 进行本地保存。
    -   **优化**: 新增 "一键同步规划数据" 功能，可从主界面同步车辆参数和路线信息。
    -   **优化**: 新增图片上传 UI 占位 (支持行驶证、身份证、轮廓图)。
    -   **优化**: 增加必填字段校验规则。
2.  **修改入口**: `src/components/RouteForm.vue` (已完成)
    -   在 "车辆配置" 下方新增 "通行资质预审信息" 入口卡片。
    -   传递 `selectedVehicle` 和 `form` 数据给子组件以支持同步。
3.  **后续完善**:
    -   数据与后端 API 对接

## 6. 待办事项 / 优化建议

- [ ] **数据结构对齐**: 确认现有 `RouteForm.vue` 中的车辆配置数据结构是否能直接复用上述 `formData` 结构，或者需要做映射。
- [ ] **必填校验**: 需确认哪些字段在智能选线阶段是必须的，哪些是后续申请才需要的（例如图片可能在选线阶段非必须）。
- [ ] **枚举值同步**: 城市选择器 (`opendb-city-china`) 和 车辆模板 (`dd-vehicle-template`) 的数据源需要与后端保持一致。
