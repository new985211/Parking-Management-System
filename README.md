# 🅿️ 停车场智能管理系统

基于 **Flask + PaddleOCR + SQLite** 的轻量级车牌识别停车场管理系统。支持车牌自动识别、出入场记录、阶梯计费、道闸联动、微信小程序车主端和在线支付。

([国内用户可以看gitee仓库])(https://gitee.com/new211/parking-management-system)
---

## 📋 目录

- [系统架构](#-系统架构)
- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
  - [环境要求](#环境要求)
  - [开发模式](#开发模式)
  - [Docker Compose 部署](#docker-compose-部署)
  - [手动部署](#手动部署)
- [API 文档](#-api-文档)
- [数据库设计](#-数据库设计)
- [计费规则](#-计费规则)
- [硬件对接](#-硬件对接)
  - [摄像头接入](#摄像头接入)
  - [道闸控制](#道闸控制)
- [微信小程序](#-微信小程序)
- [微信支付](#-微信支付)
- [测试](#-测试)
- [运维指南](#-运维指南)
- [常见问题](#-常见问题)
- [后续扩展](#-后续扩展)
- [Bug 修复历史](#-bug-修复历史)

---

## 🏗 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Nginx (Reverse Proxy)                      │
│              port 80/443 → routes to services                 │
└──────┬──────────────┬──────────────┬─────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌───────────┐ ┌──────────────────┐
│  Flask App  │ │  Static   │ │  PaddleOCR       │
│ (Gunicorn)  │ │  Files    │ │  Container       │
│  port 5000  │ │           │ │  port 5001       │
└──────┬──────┘ └───────────┘ └──────────────────┘
       │
       ├── SQLite (parking.db)
       ├── IP Camera (RTSP) → OpenCV Capture
       ├── Barrier Gate Control (Network Relay / GPIO)
       └── WeChat Pay API

┌──────────────────────────────────────────────────────────────┐
│           WeChat Mini-Program (separate codebase)             │
│  → HTTPS API calls to Flask backend                          │
│  → WeChat Pay via wx.requestPayment                          │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ 功能特性

### 核心功能

- **🔍 车牌自动识别** — PaddleOCR 识别中英文车牌（含新能源绿牌），置信度 < 85% 自动标记人工复核
- **🚗 出入场管理** — 入场自动开闸、防重复入场；出场自动计费、支持月租车免费
- **💰 阶梯计费** — 30分钟内免费，分段计费，单日封顶，月租车免停
- **📊 实时监控面板** — 今日入场/出场/在场/收入四大指标 + 最近记录滚动展示
- **📋 记录查询** — 按车牌号/日期搜索，分页浏览历史出入记录

### 扩展功能

- **📱 微信小程序** — 车主端：绑定车牌、查询记录、在线缴费、当前停车状态
- **💳 微信支付** — JSAPI 小程序支付，支持真实商户号和开发模拟模式
- **🚧 道闸联动** — 抽象道闸控制器，支持网络继电器/GPIO/RS485，入场自动抬杆
- **📹 摄像头采集** — RTSP/IP摄像头 + 运动检测，减少CPU占用
- **⚠️ 黑名单管理** — 黑名单车辆入场自动报警拒绝
- **🔐 管理员认证** — Web端登录保护，车辆管理/审核需授权

---

## 🛠 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 后端语言 |
| Flask | 3.x | Web框架 |
| PaddleOCR | 2.10+ | 车牌OCR识别 |
| PaddlePaddle | 3.x | 深度学习框架 |
| SQLite | 3 | 嵌入式数据库 |
| Docker | 28+ | 容器化部署 |
| Gunicorn | 23+ | WSGI生产服务器 |
| Nginx | latest | 反向代理 |
| OpenCV | 4.x | 摄像头采集 |
| Node.js | 22+ | 小程序开发工具链 |

---

## 📁 项目结构

```
parking-lpr/
├── docker/paddleocr/            # PaddleOCR Docker 微服务
│   ├── Dockerfile               #   容器构建文件
│   ├── requirements.txt         #   Python依赖
│   └── server.py                #   OCR HTTP服务（单例模式）
│
├── backend/                     # Flask 后端主程序
│   ├── app.py                   #   应用入口
│   ├── config.py                #   配置管理（环境变量）
│   ├── database.py              #   数据库操作层
│   ├── models.py                #   数据模型（dataclass）
│   ├── ocr_client.py            #   OCR服务HTTP客户端
│   ├── gate_controller.py       #   道闸控制器抽象层
│   ├── payment.py               #   微信支付 + 计费逻辑
│   ├── requirements.txt         #   Python依赖
│   ├── Dockerfile               #   后端容器构建
│   ├── routes/                  #   API路由模块
│   │   ├── web.py               #     页面路由
│   │   ├── api_recognize.py     #     OCR识别API
│   │   ├── api_entry_exit.py    #     出入场API
│   │   ├── api_vehicle.py       #     车辆管理API
│   │   ├── api_payment.py       #     支付API
│   │   ├── api_gate.py          #     道闸 + 审核API
│   │   ├── api_admin.py         #     管理API
│   │   └── api_miniapp.py       #     小程序专用API
│   ├── templates/               #   Jinja2 HTML模板
│   │   ├── base.html            #     基础布局（渐变色头部+导航）
│   │   ├── index.html           #     监控面板
│   │   ├── records.html         #     出入记录
│   │   ├── vehicles.html        #     车辆管理
│   │   ├── review.html          #     人工审核
│   │   └── login.html           #     管理员登录
│   ├── static/                  #   静态资源
│   │   ├── css/style.css        #     渐变色卡片风格
│   │   └── js/                  #     JavaScript
│   ├── tests/                   #   测试
│   │   ├── test_core.py         #     计费 + 车牌校验
│   │   ├── test_database.py     #     数据库操作
│   │   └── e2e_test.py          #     端到端测试
│   └── uploads/                 #   上传图片目录
│
├── capture/                     # 摄像头采集 + 道闸主控
│   ├── camera.py                #   RTSP/USB采集 + 运动检测
│   ├── gate_worker.py           #   主控循环（抓拍→识别→入场/出场→开闸）
│   └── parking-capture.service  #   systemd 服务文件
│
├── miniapp/                     # 微信小程序
│   ├── app.js / app.json / app.wxss  # 应用配置
│   ├── project.config.json      #   项目配置
│   ├── utils/api.js             #   后端API封装
│   └── pages/                   #   页面
│       ├── index/               #     我的车辆
│       ├── records/             #     停车记录
│       ├── payment/             #     停车缴费
│       └── bind/                #     绑定车牌
│
├── nginx/parking.conf           # Nginx 反向代理配置
├── docker-compose.yml           # 多服务编排
├── .env.example                 # 环境变量模板
├── deploy.md                    # 详细部署手册
└── README.md                    # 本文件
```

---

## 🚀 快速开始

### 环境要求

- **操作系统**: Ubuntu 20.04+ / Kylin V10 / Debian 系
- **Docker**: 24+ & Docker Compose v2
- **Python**: 3.11+
- **磁盘**: ≥ 5GB（PaddleOCR 模型约 2GB）
- **内存**: ≥ 4GB

### 开发模式

```bash
# 1. 克隆项目
cd parking-lpr

# 2. 启动 PaddleOCR 容器
cd docker/paddleocr
docker build -t parking-ocr .
docker run -d --name parking-ocr -p 5001:5001 parking-ocr

# 3. 启动 Flask 后端
cd ../../backend
pip install -r requirements.txt
python app.py
# → 访问 http://localhost:5000

# 4. 测试 OCR 服务
curl -F "image=@test_plate.jpg" http://localhost:5001/ocr

# 5. 模拟道闸全流程
cd ../capture
python gate_worker.py --demo
```

### Docker Compose 部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入实际配置

# 2. 构建并启动所有服务
docker compose up -d --build

# 3. 检查状态
docker compose ps
docker compose logs -f backend

# 4. 访问
# Web: http://localhost
# 默认账号: admin / admin123
```

### 手动部署

详细步骤见 [deploy.md](deploy.md)。

---

## 📡 API 文档

### 页面路由

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 实时监控面板 |
| GET | `/records` | 出入记录查询（支持 ?plate=&date=&page=） |
| GET | `/vehicles` | 车辆管理（需登录） |
| GET | `/review` | 低置信度记录人工审核（需登录） |
| GET | `/login` | 管理员登录页 |
| GET | `/health` | 健康检查 |

### 识别 & 出入场

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/recognize` | 上传图片 → OCR识别车牌 |
| POST | `/api/entry` | 车辆入场登记 |
| POST | `/api/exit` | 车辆出场 + 自动计费 |
| GET | `/api/stats` | 今日统计数据 |

#### POST `/api/recognize`

```bash
curl -F "image=@plate.jpg" http://localhost:5000/api/recognize
```

```json
{
  "success": true,
  "plate": "粤B12345",
  "confidence": 0.95,
  "need_review": false,
  "image_path": "uploads/plate_1718123456.jpg"
}
```

#### POST `/api/entry`

```bash
curl -X POST http://localhost:5000/api/entry \
  -H "Content-Type: application/json" \
  -d '{"plate": "粤B12345", "location": "main_gate", "confidence": 0.95}'
```

```json
{
  "success": true,
  "message": "粤B12345 入场成功",
  "plate": "粤B12345",
  "time": "2026-06-10 14:30:00"
}
```

#### POST `/api/exit`

```bash
curl -X POST http://localhost:5000/api/exit \
  -H "Content-Type: application/json" \
  -d '{"plate": "粤B12345"}'
```

```json
{
  "success": true,
  "plate": "粤B12345",
  "duration_seconds": 5400,
  "duration_text": "1小时30分钟",
  "fee": 5.0,
  "exit_time": "2026-06-10 16:00:00",
  "need_payment": true
}
```

### 车辆管理

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/vehicles` | 车辆列表（?plate=&type=） |
| POST | `/api/vehicles` | 注册/更新车辆 |
| PUT | `/api/vehicles/<id>` | 更新车辆信息 |
| GET | `/api/blacklist` | 黑名单列表 |
| POST | `/api/blacklist` | 加入黑名单 |
| DELETE | `/api/blacklist/<id>` | 移出黑名单 |

### 支付

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/payment/create` | 创建微信支付订单 |
| POST | `/api/payment/callback` | 微信支付回调通知 |
| GET | `/api/payment/status` | 查询支付状态 |

### 管理 & 统计

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/login` | 管理员登录 |
| GET | `/api/recent` | 最近 20 条出入记录（AJAX 刷新用） |
| GET | `/api/stats/weekly` | 近 7 天车流统计 |

### 道闸 & 审核

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/gate/open` | 手动开闸 |
| POST | `/api/gate/close` | 手动关闸 |
| GET | `/api/gate/status` | 道闸状态 |
| POST | `/api/review/confirm` | 确认/修正车牌 |

### 小程序专用

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/miniapp/login` | 微信登录（code → openid） |
| GET | `/api/miniapp/vehicle` | 获取绑定车辆 |
| POST | `/api/miniapp/bind` | 绑定/解绑车牌 |
| GET | `/api/miniapp/records` | 停车记录 |
| GET | `/api/miniapp/current` | 当前停车状态 |
| GET | `/api/miniapp/stats` | 用户统计 |

---

## 🗄 数据库设计

| 表 | 用途 | 关键字段 |
|----|------|----------|
| `users` | 管理员账户 | username, password_hash, role |
| `vehicles` | 注册车辆 | plate_number, owner_name, vehicle_type, monthly_fee, wechat_openid |
| `records` | 出入记录 | plate_number, event_type, confidence, need_review, parking_duration, fee |
| `payments` | 支付记录 | record_id, amount, method, transaction_id, status |
| `gates` | 道闸设备 | name, direction, control_type, control_address, status |
| `blacklist` | 黑名单 | plate_number, reason |

**索引**: records(plate_number, created_at, event_type), payments(record_id, transaction_id), vehicles(wechat_openid)

---

## 💰 计费规则

| 停车时长 | 收费标准 | 说明 |
|----------|----------|------|
| ≤ 30 分钟 | **免费** | 临停友好 |
| 30 分 ~ 2 小时 | **5 元** | 短时停车 |
| 2 小时 ~ 4 小时 | **10 元** | 中等时长 |
| > 4 小时 | **10元 + 3元/小时** | 阶梯计费 |
| 单日封顶 | **50 元** | 防止天价 |
| 月租车 | **免费** | 已缴费业主 |

> 计费规则可通过 `config.py` 调整：`FREE_MINUTES`, `SHORT_TERM_FEE`, `DAILY_CAP` 等。

---

## 🔌 硬件对接

### 摄像头接入

支持三种方案：

| 方案 | 成本 | 难度 | 适用场景 |
|------|------|------|----------|
| USB摄像头 | ¥100-300 | ⭐ | 小停车场/测试 |
| IP摄像头(RTSP) | ¥200-800 | ⭐⭐ | **推荐：中型以上停车场** |
| 道闸一体机 | ¥2000-5000 | ⭐⭐⭐ | 商业项目 |

**海康威视 RTSP 格式**:
```
rtsp://admin:password@192.168.1.64:554/h264/ch1/main/av_stream
```

**大华 RTSP 格式**:
```
rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0
```

**运动检测**: `capture/camera.py` 内置 `cv2.absdiff()` 运动检测，有车经过时才触发识别，避免 24/7 全帧处理。

### 道闸控制

通过抽象层 `GateController` 支持：

| 方案 | 说明 |
|------|------|
| **NetworkRelayController** | HTTP/TCP 网络继电器（默认），适用于 Waveshare 等模块 |
| **GPIOController** | 树莓派 GPIO 直连继电器 |
| **SimulatedController** | 开发/测试用，打印日志不执行硬件操作 |

```bash
# 使用真实继电器
GATE_TYPE=network_relay GATE_RELAY_HOST=192.168.1.200 python capture/gate_worker.py

# 模拟模式
python capture/gate_worker.py --demo
```

---

## 📱 微信小程序

### 页面

| 页面 | 功能 |
|------|------|
| **我的车辆** | 显示绑定车牌、当前停车状态、时长和费用 |
| **停车记录** | 历史出入记录，分页加载 |
| **停车缴费** | 微信支付缴纳停车费，支付成功后自动开闸 |
| **绑定车牌** | 绑定/解绑车牌到微信账号 |

### 配置步骤

1. 注册微信小程序：https://mp.weixin.qq.com
2. 获取 AppID 和 AppSecret
3. 修改 `miniapp/utils/api.js` 中 `apiBase` 为你的服务器地址
4. 修改 `miniapp/project.config.json` 中 `appid`
5. 用微信开发者工具打开 `miniapp/` 目录

---

## 💳 微信支付

### 支付流程

```
用户点击"缴费" → 后端创建订单 → wx.requestPayment() → 用户确认支付
    → 微信回调 /api/payment/callback → 更新订单状态 → 开闸放行
```

### 配置

在 `.env` 中设置：

```bash
WECHAT_APP_ID=wx1234567890
WECHAT_APP_SECRET=your_app_secret
WECHAT_MCH_ID=1234567890
WECHAT_API_KEY=your_merchant_api_key
WECHAT_NOTIFY_URL=https://your-domain.com/api/payment/callback
```

> 未配置微信支付时，系统自动使用模拟支付模式（`_simulated: true`），方便开发测试。

---

## 🧪 测试

```bash
cd backend

# 安装测试依赖
pip install pytest requests

# 运行单元测试（计费 + 车牌校验 + 数据库）
python -m pytest tests/ -v

# 运行 E2E 测试（需先启动后端）
python app.py &                    # 启动后端
python tests/e2e_test.py           # 运行端到端测试

# 测试道闸全流程（模拟模式）
cd ../capture
python gate_worker.py --demo
```

**测试覆盖**:
- ✅ 计费逻辑：7 个测试（免费/短时/中时/长时/封顶/月租/VIP）
- ✅ 车牌校验：4 个测试（标准/新能源/非法/纠错）
- ✅ 数据库：8 个测试（建表/默认数据/CRUD/黑名单/入场查询/openid绑定）
- ✅ E2E：15 个测试（需运行后端，覆盖所有 API 端点）

---

## 🔧 运维指南

### 启动/停止

```bash
# Docker Compose
docker compose up -d              # 启动
docker compose down               # 停止
docker compose restart backend    # 重启后端

# systemd（摄像头 worker）
systemctl start parking-capture
systemctl stop parking-capture
systemctl status parking-capture
```

### 日志

```bash
docker compose logs -f backend        # 后端日志
docker compose logs -f ocr            # OCR服务日志
journalctl -u parking-capture -f      # 摄像头worker日志
```

### 数据库备份

```bash
# 手动备份
cp data/parking.db backups/parking-$(date +%Y%m%d).db

# 自动备份（crontab）
0 3 * * * cp /opt/parking-lpr/data/parking.db /backup/parking-$(date +\%Y\%m\%d).db
```

### 健康检查

```bash
curl http://localhost/health
# {"status":"ok","service":"parking-lpr","time":"2026-06-10T14:30:00"}
```

### 性能参考

- **200车位** 停车场：SQLite 足够（年数据量 ~73MB）
- **1000车/天**：平均每分钟 < 1辆，无需消息队列
- **5000+车位**：建议升级 PostgreSQL + Celery 消息队列

---

## ❓ 常见问题

### PaddleOCR 模型下载慢？

```bash
# 使用百度镜像加速
export PADDLE_PIPmirror=https://mirror.baidu.com
pip install paddlepaddle
```

### 识别率不高？

| 问题 | 解决方案 | 提升幅度 |
|------|----------|----------|
| 图片模糊 | 换高清摄像头（≥1080p） | +15% |
| 光线暗 | 加装补光灯 | +10% |
| 角度偏 | 调整摄像头正对车道 | +8% |
| 车牌脏 | 人工复核 | — |
| 新能源绿牌 | PaddleOCR 2.7+ 已支持 | — |

### 并发高怎么办？

200车位级别不需要消息队列。如确有需要，可使用 Celery + Redis：

```python
from celery import Celery
celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def recognize_async(image_path):
    return recognize(image_path)
```

### 如何修改计费规则？

编辑 `backend/config.py`：

```python
FREE_MINUTES = 30          # 免费分钟数
SHORT_TERM_FEE = 5.0       # 30分钟-2小时
MEDIUM_TERM_FEE = 10.0     # 2小时-4小时
EXTRA_HOURLY_RATE = 3.0    # 超4小时后每小时
DAILY_CAP = 50.0            # 单日封顶
```

---

## 🚧 后续扩展

| 功能 | 难度 | 价值 |
|------|------|------|
| 📊 数据报表 | ⭐ | 周/月/年收入统计、车流高峰分析 |
| 🔔 短信通知 | ⭐ | 入场/出场/缴费成功短信提醒 |
| 🎫 优惠券系统 | ⭐⭐ | 商户发放停车优惠券 |
| 📹 多路摄像头 | ⭐⭐ | 支持多个出入口同时监控 |
| 🏢 多停车场管理 | ⭐⭐ | 一个系统管理多个停车场 |
| 🧠 深度学习优化 | ⭐⭐⭐ | 自定义车牌检测模型 |
| 🔄 云端同步 | ⭐⭐ | 数据同步到云数据库 |

---

## 🐛 Bug 修复历史

| # | 严重度 | 修复日期 | 模块 | 问题 | 修复 |
|---|--------|----------|------|------|------|
| 1 | 🔴 Critical | 2026-06-11 | `normalize_plate()` | `B→8, S→5, D→0, Z→2, L→1` 字符替换破坏合法车牌城市代码（如粤B→粤8） | 仅保留 `O→0` 和 `I→1`（这两个字母从未在中国车牌中使用） |
| 2 | 🔴 Critical | 2026-06-11 | `find_best_plate()` | 高置信度非车牌文本（如"停车场入口" 0.95）会阻止低置信度有效车牌（如"粤B12345" 0.85）被选中 | 分离 valid 和 fallback 两条跟踪路径，有效车牌永远优先 |
| 3 | 🟡 Medium | 2026-06-11 | `upsert_vehicle()` | INSERT 和 UPDATE 均缺少 `monthly_expire` 字段 | 添加参数并更新 SQL |
| 4 | 🟡 Medium | 2026-06-11 | 出入场 SQL | `r2.created_at > r1.created_at` 使用严格大于，同一秒出入场会丢失记录 | 改为 `>=` |
| 5 | 🟢 Low | 2026-06-11 | `verify_callback()` | 参数名 `Headers` 大写 H 不符合 Python 规范 | 改为 `headers` |
| 6 | 🟢 Low | 2026-06-11 | `server.py` | 未使用的 `from io import BytesIO` 导入 | 删除 |
| 7 | 🔴 Critical | 2026-06-11 | 登录页 | 登录 JS 依赖 `dashboard.js` 中的函数但加载顺序不可靠；界面仅为白色卡片 + emoji | 重写为自包含 fetch 逻辑 + 全屏渐变背景 + 独立 CSS |
| 8 | 🟡 Medium | 2026-06-11 | Deploy-Offline | CSS/JS/nginx/docker-compose/.env 均为 v1 过期版本 | 同步到当前版本 |
| 9 | 🟢 Low | 2026-06-11 | `records.js` | 空占位符文件，无实际功能 | 删除 |

---

## 📄 License

MIT License

---

## 🙏 致谢

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — 百度开源OCR引擎
- [Flask](https://flask.palletsprojects.com/) — Python Web微框架
- 如果觉得好用，欢迎点个 Star 或者打赏支持：

  ![sponsor](assets/zxq.jpg)
