# 🅿️ 停车场智能管理系统

基于 **Flask + PaddleOCR + SQLite** 的轻量级车牌识别停车场管理系统。200 个车位规模，年维护成本从外包的 5 万降至 0。

## ✨ 功能特性

### 核心功能
- **🔍 车牌自动识别** — PaddleOCR 中英文车牌（含新能源绿牌），置信度 < 85% 自动标记人工复核
- **🚗 出入场管理** — 入场开闸、防重复入场；出场自动阶梯计费、月租车免费
- **💰 智能计费** — ≤30分钟免费，30分-2时 5元，2-4时 10元，>4时 每小时+3元，单日封顶50元
- **📊 实时面板** — 今日入场/出场/在场/收入 4 大指标，30秒 AJAX 无闪烁刷新
- **📋 记录查询** — 车牌/日期搜索、分页浏览、表头点击排序

### 扩展功能
- **📱 微信小程序** — 车主绑定车牌、查看停车记录、查看当前费用、在线缴费
- **💳 微信支付** — JSAPI 小程序支付，开发环境自动模拟
- **🚧 道闸联动** — 抽象 GateController，支持网络继电器 / GPIO / RS485
- **📹 智能采集** — RTSP 摄像头 + 运动检测，有车才触发 OCR
- **⚠️ 黑名单** — 黑名单车辆入场自动拒绝并告警
- **🔐 管理后台** — 管理员登录、车辆管理、低置信度人工审核

### 交互体验 (UI v3)
- **🌙 深色模式** — 一键切换 + `prefers-color-scheme` 自动检测 + localStorage 持久化
- **📋 复制车牌** — 点击任意车牌一键复制到剪贴板
- **↩️ 撤销操作** — 关键操作 6 秒内可撤回
- **⌨️ 全键盘** — Alt+D/R/V 导航、`/` 聚焦搜索、`?` 帮助、Escape 关闭
- **📱 移动端** — 汉堡菜单 + 固定底部导航栏 + 表格自适应卡片视图
- **🖨️ 打印优化** — `@media print` 隐藏 UI 元素，纯内容打印
- **♿ 无障碍** — skip-link + focus-visible + ARIA 标签 + prefers-reduced-motion

## 🏗 系统架构

```
┌─────────────────────────────────────────────────┐
│              Nginx :80/443                       │
│         static /uploads   proxy_pass             │
└──────┬──────────────────────┬───────────────────┘
       │                      │
       ▼                      ▼
┌──────────────┐    ┌──────────────────┐
│  Flask App   │───▶│  PaddleOCR :5001 │
│  Gunicorn    │    │  (Docker独立容器)  │
│  :5000       │    └──────────────────┘
└──────┬───────┘
       │ SQLite (parking.db)
       │ IP Camera (RTSP → OpenCV)
       │ Barrier Gate (Network Relay)
       │ WeChat Pay API
       ▼
┌──────────────────────────┐
│  WeChat Mini-Program     │
│  HTTPS API → 后端       │
│  wx.requestPayment      │
└──────────────────────────┘
```

## 🛠 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.11 + Flask 3.x | REST API + Jinja2 模板 |
| OCR | PaddleOCR 2.10 + PaddlePaddle 3.x | Docker 独立容器 |
| 数据库 | SQLite 3 (WAL mode) | 200 车位年数据 ~73MB |
| 前端 | 原生 CSS + JS (1103+579 行) | CSS 自定义属性设计系统 |
| 部署 | Docker Compose + Gunicorn + Nginx | 3 容器编排 |
| 小程序 | WeChat Mini-Program | 4 页面：车辆/记录/缴费/绑定 |
| 支付 | WeChat Pay API v3 | JSAPI + 回调 |

## 📁 项目结构

```
parking-lpr/
├── docker/paddleocr/        # PaddleOCR Docker 微服务
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py            # OCR HTTP 服务（车牌校验+纠错）
│
├── backend/                 # Flask 后端
│   ├── app.py               # 主入口
│   ├── config.py            # 环境配置
│   ├── database.py          # SQLite 操作层
│   ├── models.py            # 数据模型 (dataclass)
│   ├── ocr_client.py        # OCR HTTP 客户端（重试+指数退避）
│   ├── gate_controller.py   # 道闸抽象 (NetworkRelay/GPIO/Simulated)
│   ├── payment.py           # 微信支付 + 计费逻辑
│   ├── routes/              # API 路由
│   │   ├── web.py               # 页面路由 (dashboard/records/vehicles/review/login)
│   │   ├── api_recognize.py     # OCR 识别
│   │   ├── api_entry_exit.py    # 出入场
│   │   ├── api_vehicle.py       # 车辆 CRUD + 黑名单
│   │   ├── api_payment.py       # 支付创建/回调/查询
│   │   ├── api_gate.py          # 道闸控制 + 人工审核
│   │   ├── api_admin.py         # 登录/统计/分组统计
│   │   └── api_miniapp.py       # 小程序专用 (login/bind/current)
│   ├── templates/           # Jinja2 模板
│   │   ├── base.html            # 基础布局 (skip-link + 汉堡菜单 + 底部导航)
│   │   ├── index.html           # 监控面板 (AJAX刷新 + 周趋势占位)
│   │   ├── records.html         # 记录查询 (可排序表头 + 移动卡片视图)
│   │   ├── vehicles.html        # 车辆管理 (表单验证 + 月租到期日)
│   │   ├── review.html          # 人工审核 (Enter 键确认 + 对话框)
│   │   └── login.html           # 管理员登录 (全屏渐变 + 独立 JS)
│   ├── static/
│   │   ├── css/style.css        # 设计系统 (1103行, CSS变量, 深色模式)
│   │   └── js/dashboard.js      # 交互层 (579行, Toast/Confirm/Undo/Copy/Sort)
│   ├── tests/
│   │   ├── test_core.py         # 35 测试 (计费/校验/纠错/优先逻辑)
│   │   ├── test_database.py     # 10 测试 (数据库 CRUD)
│   │   └── e2e_test.py          # 15 测试 (需运行后端)
│   └── Dockerfile
│
├── capture/                 # 摄像头 + 道闸主控
│   ├── camera.py            # RTSP/USB 采集 + MotionDetector
│   ├── gate_worker.py       # 主控循环 (demo 模式可独立测试)
│   └── parking-capture.service  # systemd 服务
│
├── miniapp/                 # 微信小程序
│   ├── app.js/json/wxss     # 应用配置 (骨架屏 + 品牌支付按钮)
│   ├── utils/api.js         # 后端 API 封装
│   └── pages/               # index(我的车辆)/records(记录)/payment(缴费)/bind(绑定)
│
├── nginx/parking.conf       # Nginx 反向代理 (限流 + OCR 长超时)
├── docker-compose.yml       # 3 服务编排 (ocr/backend/nginx)
├── .env.example             # 环境变量模板 (17 变量)
├── deploy.md                # 生产部署手册
└── README.md                # 本文件
```

## 🚀 快速开始

```bash
# 1. 环境准备
cp .env.example .env

# 2. 一键启动
docker compose up -d --build

# 3. 访问
#    Web:  http://localhost
#    API:  curl http://localhost/health
#    登录: admin / admin123

# 4. 测试全流程（模拟道闸）
docker exec parking-backend python -c "
import requests
r=requests.post('http://localhost:5000/api/entry',json={'plate':'粤B12345','confidence':0.95})
print(r.json())
r=requests.post('http://localhost:5000/api/exit',json={'plate':'粤B12345'})
print(r.json())"
```

## 📡 API 速查

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/` | 监控面板 |
| GET | `/records?plate=&date=&page=` | 记录查询 |
| GET/POST | `/api/vehicles` | 车辆列表/新增 |
| POST | `/api/recognize` | 上传图片 → OCR |
| POST | `/api/entry` | 车辆入场 |
| POST | `/api/exit` | 车辆出场+计费 |
| GET | `/api/stats` | 今日统计 |
| GET | `/api/recent` | 最近 20 条记录 |
| POST | `/api/login` | 管理员登录 |
| POST | `/api/payment/create` | 创建支付 |
| POST | `/api/payment/callback` | 支付回调 |
| POST | `/api/gate/open` | 手动开闸 |
| GET | `/health` | 健康检查 |

## 🧪 测试

```bash
cd backend
pip install pytest requests
python -m pytest tests/ -v
# 48 passed, 15 skipped (E2E 需后端运行)
```

## 📄 License

MIT License
