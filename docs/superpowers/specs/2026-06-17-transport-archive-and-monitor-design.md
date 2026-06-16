# 运输过程数字档案 + 护送监控面板 设计文档

**日期**: 2026-06-17
**状态**: 设计中 → 待评审

---

## 1. 概述

### 1.1 目标

1. **运输过程数字档案**：记录运输全过程的GPS轨迹、检查点通行、异常事件，支持一键导出结构化证据链
2. **护送监控面板**：实时展示运输车辆在地图上的位置、速度、方向，异常即时告警

### 1.2 对标

| 功能 | 江苏 | 广西 | Bentley | 本方案 |
|------|------|------|---------|--------|
| GPS实时跟踪 | - | 北斗+IoT | - | SSE模拟推送 |
| 检查点记录 | - | 关键路段 | 桥梁分析记录 | 桥梁/隧道/施工区逐段 |
| 异常告警 | - | 1.5秒推送 | - | 偏航/超速/延误 |
| 数字档案导出 | 全流程记录 | 历史数据AI训练 | 完整审计追踪 | JSON/PDF一键导出 |
| 轨迹回放 | - | - | 历史热力图 | 时间轴+地图回放 |

### 1.3 依赖

- 无新增外部API依赖
- 复用已有 Amap route polyline 数据
- 复用已有 SSE 推送模式（agent_service.py）
- 复用已有 tracking_models（TransportOrder, StatusLog）

---

## 2. 架构设计

```
┌─ Amap Route Polyline (已有) ─┐
│  从route_data获取完整坐标串    │
└──────────────┬────────────────┘
               ▼
┌─ GPS Simulator (gps_simulator.py) ─┐
│  沿polyline匀速移动，每5秒生成       │
│  {lon, lat, speed, heading, time}   │
│  在检查点位置自动生成通过事件        │
│  随机注入小概率异常（供测试）        │
└──────────────┬──────────────────────┘
               ▼
    ┌───── SSE Stream ─────┐
    │  event: gps          │──→ MonitorDashboard.vue 地图实时移动
    │  event: checkpoint   │──→ 检查点通过列表更新
    │  event: alert        │──→ 告警面板实时推送
    │  event: status       │──→ 运输状态更新
    └──────────────────────┘
               │
               ▼ (同时写入DB)
┌─ 数字档案 (archive_service.py) ────┐
│  数据表:                             │
│  • gps_track_points    GPS轨迹点     │
│  • checkpoint_records  检查点记录     │
│  • alert_events        异常事件       │
│                                     │
│  导出: JSON / PDF                   │
└─────────────────────────────────────┘
```

---

## 3. 后端设计

### 3.1 GPS模拟器 `backend/app/services/gps_simulator.py`

**职责**：从路线polyline生成模拟GPS位置流

```python
class GPSSimulator:
    def __init__(self, polyline: str, checkpoints: list[dict]):
        """
        polyline: Amap polyline string (分号分隔的 "lon,lat" 坐标)
        checkpoints: 沿途检查点列表 [{station, type, highway, lon, lat}]
        """

    async def run(self, speed_kmh: float = 60) -> AsyncGenerator:
        """沿polyline匀速移动，每5秒yield一个GPS点。
        经过检查点时额外yield checkpoint事件。
        随机注入异常（<5%概率）用于测试告警。
        """

    def calculate_position(self, elapsed_seconds: float) -> dict:
        """根据已过时间在polyline上插值计算当前位置"""

    def check_nearby_checkpoints(self, current_pos: dict) -> list[dict]:
        """检测当前位置附近（<200m）的检查点"""
```

**关键逻辑**：
- 使用 polyline 的累计距离表做二分查找定位
- 速度默认60km/h，可通过API参数调整
- 异常注入类型：偏航(偏移50m)、超速(>80km/h)、停车(速度<5km/h持续30秒)

### 3.2 监控服务 `backend/app/services/monitor_service.py`

**职责**：管理监控会话，SSE事件流

```python
class MonitorService:
    active_sessions: dict[str, dict]  # order_id -> session state

    async def start_monitoring(self, order_id: str, db: Session) -> dict:
        """初始化监控会话：加载路线数据、创建GPS模拟器、更新订单状态为IN_TRANSIT"""

    async def stream_events(self, order_id: str) -> AsyncGenerator[str, None]:
        """SSE事件流生成器。
        事件类型:
        - gps:        {lon, lat, speed, heading, timestamp, distance_remaining}
        - checkpoint: {station, type, highway, passed_at}
        - alert:      {type, message, severity, timestamp}
        - status:     {status, message}
        - done:       监控结束
        """

    async def stop_monitoring(self, order_id: str, db: Session) -> dict:
        """停止模拟，将缓冲数据写入数据库，更新订单状态为COMPLETED"""
```

**SSE事件格式**：
```
event: gps
data: {"lon":119.296,"lat":26.074,"speed":58.3,"heading":142,"timestamp":"2026-06-17T10:30:05","distance_remaining":234.5}

event: checkpoint
data: {"station":"K2230+500","type":"bridge","highway":"G15沈海高速","passed_at":"2026-06-17T10:31:20"}

event: alert
data: {"type":"speed_warning","message":"超速警告: 当前速度85km/h (限速80km/h)","severity":"high","timestamp":"2026-06-17T10:35:00"}
```

### 3.3 档案服务 `backend/app/services/archive_service.py`

**职责**：聚合数据，生成档案，导出

```python
class ArchiveService:
    def generate_archive(self, order_id: str, db: Session) -> dict:
        """聚合运输全过程数据:
        {
          order_info: {...},
          timeline: [...],
          gps_summary: {total_distance, avg_speed, max_speed, duration},
          checkpoints: [{station, type, passed_at, delay_minutes}],
          alerts: [{type, message, severity, timestamp}],
          bridge_records: [{station, ratio, grade, passed_normally}],
          attachments: [...]
        }
        """

    def export_json(self, order_id: str, db: Session) -> str:
        """导出为结构化JSON文件"""

    def export_pdf(self, order_id: str, db: Session) -> bytes:
        """导出为PDF报告（使用reportlab或weasyprint）"""
```

### 3.4 数据模型扩展 `backend/app/models/tracking_models.py`

新增三张表：

```python
class GPSTrackPoint(Base):
    __tablename__ = "gps_track_points"
    id, order_id(FK), longitude, latitude, speed, heading,
    timestamp, is_simulated(bool)

class CheckpointRecord(Base):
    __tablename__ = "checkpoint_records"
    id, order_id(FK), station, checkpoint_type(桥/隧/收费站/施工区),
    highway, longitude, latitude, planned_pass_time, actual_pass_time,
    delay_minutes, notes

class AlertEvent(Base):
    __tablename__ = "alert_events"
    id, order_id(FK), alert_type(speed/deviation/stop/delay),
    message, severity(low/medium/high/critical),
    longitude, latitude, timestamp, resolved(bool)
```

### 3.5 API路由 `backend/app/api/monitor_routes.py`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/monitor/start/{order_id}` | 开始监控，启动GPS模拟 |
| GET | `/monitor/stream/{order_id}` | SSE事件流 (text/event-stream) |
| POST | `/monitor/stop/{order_id}` | 停止监控，数据归档 |
| GET | `/monitor/sessions` | 列出活跃监控会话 |
| GET | `/archive/{order_id}` | 获取数字档案 |
| GET | `/archive/{order_id}/export?format=json` | 导出档案 |

---

## 4. 前端设计

### 4.1 护送监控面板 `MonitorDashboard.vue`

**布局**：大屏三栏式

```
┌─────────────────────────────────────────────────┐
│ 🚛 运输单号: TR20260617-001 | 📍 G15 K2230+500 │
│ 🏃 当前速度: 58km/h | 🎯 距目的地: 234.5km     │
│ ⏱ 已行驶: 1h23m | 预计到达: 12:30              │
├───────────────────────┬─────────────────────────┤
│                       │  检查点通过列表          │
│   Amap 地图          │  ┌─────────────────┐    │
│   (占2/3宽度)        │  │ ✅ 东寨枢纽  10:05│   │
│                       │  │ ✅ K2230桥   10:15│   │
│   🚛 ← 实时移动       │  │ ⏳ K2276施工  --:--│  │
│   marker             │  │ ⬜ 海沧枢纽   --:--│  │
│                       │  └─────────────────┘    │
│                       ├─────────────────────────┤
│                       │  告警面板               │
│                       │  🔴 超速 K2240 10:35   │
│                       │  🟡 偏航 K2280 10:42   │
│                       │  🟢 正常                │
├───────────────────────┴─────────────────────────┤
│ [开始监控] [暂停] [停止] [导出档案]              │
└─────────────────────────────────────────────────┘
```

**技术要点**：
- 使用 Amap JS API v2.0 加载地图，绘制路线和 marker
- SSE EventSource 或 fetch+ReadableStream 接收事件
- marker 沿 polyline 平滑移动（线性插值）
- 检查点列表和告警列表实时更新

### 4.2 数字档案查看器 `TransportArchive.vue`

**布局**：双模式切换

**模式1 — 时间线视图**：
```
┌─ 时间轴滑块 ────────────────────────────────────┐
│ [10:00]══════[10:30]══════[11:00]══════[11:30]  │
│  发车         通过东寨      通过K2230      当前位置│
└─────────────────────────────────────────────────┘
┌─ 事件列表（可滚动）───────────────────────────┐
│ 10:00  🟢 发车，三明北收费站出发               │
│ 10:05  ✅ 通过检查点: 东寨枢纽                  │
│ 10:15  ✅ 通过桥梁: K2230+500 (效应比0.42,正常) │
│ 10:35  🔴 告警: 超速85km/h (K2240+000)         │
│ 10:42  🟡 告警: 偏航50m (K2280+000)            │
│ 11:00  ✅ 通过施工区: K2277+599~K2313+637       │
└────────────────────────────────────────────────┘
[导出JSON] [导出PDF]
```

**模式2 — 轨迹回放**：
- 地图上按时间轴回放GPS轨迹
- 可调速（1x / 2x / 5x / 10x）
- 检查点和告警在地图上标注闪烁

---

## 5. 数据流

```
1. 用户在 StatusDashboard 选择一个已发证的运输单
2. 点击"开始监控" → POST /monitor/start/{order_id}
3. 后端: 
   a. 加载订单的 route_data_json.polyline
   b. 从 bridge_assessment + construction_match 提取检查点坐标
   c. 创建 GPSSimulator 实例
   d. 更新订单状态为 IN_TRANSIT
4. 前端跳转到 MonitorDashboard → GET /monitor/stream/{order_id} (SSE)
5. 每5秒:
   a. 后端推送 gps 事件 → 前端地图 marker 移动
   b. 经过检查点 → 推送 checkpoint 事件
   c. 异常检测 → 推送 alert 事件
   d. 所有数据同时写入 DB
6. 用户点击"停止监控" → POST /monitor/stop/{order_id}
7. 后端: 
   a. 停止GPS模拟
   b. 将缓冲区数据批量写入 DB
   c. 生成数字档案
   d. 更新订单状态为 COMPLETED
8. 前端跳转到 TransportArchive 查看档案
```

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 订单无路线数据 | /monitor/start 返回 400 "该订单无路线polyline数据" |
| 订单状态不是 PERMIT_ISSUED | 返回 400 "只能对已发证的订单启动监控" |
| SSE连接断开 | 前端自动重连（指数退避，最多3次） |
| GPS模拟数据异常 | 跳过异常点，推送 alert 事件，继续模拟 |
| 数据库写入失败 | 数据暂存内存缓冲区，SSE继续推送，定期重试写入 |
| 同一订单重复启动 | 返回 409 "该订单已有活跃监控会话" |

---

## 7. 测试策略

### 单元测试
- `gps_simulator.py`: polyline插值精度、检查点检测距离、异常注入概率
- `archive_service.py`: 档案聚合完整性、JSON/PDF导出格式

### 集成测试
- `test_monitor_api.py`: SSE流事件类型和格式、监控生命周期（启动→运行→停止）
- `test_archive_api.py`: 档案查询和导出

### E2E测试
- Playwright: 启动监控 → 验证SSE事件 → 地图marker移动 → 停止 → 档案生成

---

## 8. 文件清单

### 新增文件
```
backend/app/services/gps_simulator.py       (~120行)
backend/app/services/monitor_service.py      (~200行)
backend/app/services/archive_service.py      (~180行)
backend/app/api/monitor_routes.py            (~150行)
backend/tests/test_gps_simulator.py          (~80行)
backend/tests/test_monitor_api.py            (~120行)
frontend/src/components/MonitorDashboard.vue (~350行)
frontend/src/components/TransportArchive.vue (~250行)
frontend/src/api/monitor.js                  (~60行)
frontend/src/api/archive.js                  (~40行)
```

### 修改文件
```
backend/app/models/tracking_models.py  (+60行, 新增3个表)
backend/app/main.py                     (+2行, 注册monitor路由)
backend/app/services/tracking_service.py (+20行, 扩展update_status)
frontend/src/router/                    (+2行, 新路由)
frontend/src/api/index.js               (+2行, 导出新模块)
```

---
## 9. 自检

- [x] 无TBD/TODO占位符
- [x] 告警严重级别已明确：low(提示) / medium(警告) / high(严重) / critical(紧急停止)
- [x] API路径与现有风格一致（/api/v1前缀）
- [x] 字段名统一使用 total_weight
- [x] 错误场景已覆盖
- [x] 测试策略已定义
- [x] 不引入新的外部API依赖
