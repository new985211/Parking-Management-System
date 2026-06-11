# Parking LPR System — Production Deployment Guide

## Prerequisites

- Ubuntu 20.04+ / Kylin V10 (Debian-based) or any Linux with Docker
- Docker 24+ & Docker Compose v2
- Python 3.11+ (for camera capture worker on host)
- ≥ 5GB disk (PaddleOCR model ~2GB), ≥ 4GB RAM

## Quick Start (Development)

```bash
# 1. Clone and enter project
cd parking-lpr

# 2. Copy and edit environment
cp .env.example .env
# Set at minimum: SECRET_KEY

# 3. Start all services
docker compose up -d --build

# 4. Access
# Web:      http://localhost
# OCR API:  http://localhost:5001/ocr
# Login:    admin / admin123

# 5. Test full pipeline (simulated gate)
docker exec parking-backend python -c "
import requests; requests.post('http://localhost:5000/api/entry',
json={'plate':'粤B12345','confidence':0.95})"
```

## Production Deployment

### Option A: Docker Compose (Recommended)

```bash
cd parking-lpr
mkdir -p data
cp .env.example .env
# Edit .env with real values (see Configuration section below)

docker compose up -d --build
docker compose ps      # verify all 3 services running
```

### Option B: Manual (Host-level)

```bash
# 1. PaddleOCR container
docker build -t parking-ocr docker/paddleocr/
docker run -d --name parking-ocr --restart always -p 5001:5001 parking-ocr

# 2. Flask Backend with Gunicorn
cd backend
pip install -r requirements.txt
gunicorn -w 4 -b 127.0.0.1:5000 app:app --access-logfile /var/log/parking/access.log

# 3. Nginx (optional for production)
cp nginx/parking.conf /etc/nginx/conf.d/parking.conf
nginx -t && systemctl reload nginx

# 4. Camera Worker (systemd, optional)
cp capture/parking-capture.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now parking-capture
```

## Environment Variables

All configurable via `.env` file. See `.env.example` for full list.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | — | Flask secret key (≥32 random chars) |
| `DB_PATH` | No | `parking.db` | SQLite database path |
| `OCR_SERVICE_URL` | No | `http://ocr:5001/ocr` | PaddleOCR endpoint |
| `WECHAT_APP_ID` | For mini-program | — | WeChat Mini-Program AppID |
| `WECHAT_APP_SECRET` | For mini-program | — | WeChat Mini-Program AppSecret |
| `WECHAT_MCH_ID` | For payment | — | WeChat Pay merchant ID |
| `WECHAT_API_KEY` | For payment | — | WeChat Pay API v3 key |
| `WECHAT_NOTIFY_URL` | For payment | — | Payment callback URL |
| `GATE_RELAY_HOST` | For gate | `192.168.1.200` | Network relay IP |
| `GATE_RELAY_PORT` | For gate | `80` | Network relay port |
| `RTSP_URL` | For camera | — | RTSP camera stream URL |
| `GATE_TYPE` | For gate worker | `simulated` | `network_relay` / `gpio` / `simulated` |

## Database

SQLite auto-created on first run. Docker mount: `./data/parking.db` on host.

**Backup:**
```bash
# Manual
cp data/parking.db backups/parking-$(date +%Y%m%d).db

# Cron (daily at 3 AM)
0 3 * * * cp /opt/parking-lpr/data/parking.db /backup/parking-$(date +\%Y\%m\%d).db
```

## Default Login

- **URL:** `http://your-server/login`
- **Username:** `admin`
- **Password:** `admin123`
- **⚠️ Change after first login!**

## Camera Setup

### Hikvision RTSP
```
rtsp://admin:password@192.168.1.64:554/h264/ch1/main/av_stream
```

### Dahua RTSP
```
rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0
```

**Motion detection:** Built into `capture/camera.py` — only triggers OCR when vehicle movement detected.

## WeChat Mini-Program Setup

1. Register at https://mp.weixin.qq.com
2. Get AppID and AppSecret
3. Set `WECHAT_APP_ID` / `WECHAT_APP_SECRET` in `.env`
4. Open `miniapp/` in WeChat DevTools
5. Edit `miniapp/app.js` → `apiBase` to your HTTPS server URL
6. Upload and submit for review

## WeChat Pay Setup

1. Register merchant: https://pay.weixin.qq.com
2. Get MCH ID, API v3 key, and certificates
3. Set in `.env`: `WECHAT_MCH_ID`, `WECHAT_API_KEY`, `WECHAT_NOTIFY_URL`
4. Place certs at `WECHAT_CERT_PATH` / `WECHAT_KEY_PATH`
5. In dev mode (unset MCH_ID), payments are simulated

## Monitoring

```bash
# Service status
docker compose ps
systemctl status parking-capture

# Logs
docker compose logs -f backend
journalctl -u parking-capture -f

# Health check
curl http://localhost/health
# → {"status":"ok","service":"parking-lpr"}

# Stats API
curl http://localhost/api/stats

# DB stats
sqlite3 data/parking.db "SELECT COUNT(*) FROM records WHERE DATE(created_at)=DATE('now')"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OCR returns empty | `docker logs parking-ocr` — model may still be loading (1-2 min on first start) |
| Build fails: `libGL.so.1` | Already fixed in Dockerfile — rebuild with `--no-cache` if stale |
| Build fails: `gcc` not found | Already fixed — Dockerfile installs `gcc` + `g++` |
| Backend won't start | Check OCR is healthy: `curl localhost:5001/health` |
| Login not working | Reset: `sqlite3 data/parking.db "UPDATE users SET password_hash=(SELECT password_hash FROM users WHERE username='admin')"` |
| "已在场内" error | Vehicle already has active entry — record an exit first |
| Nginx 502 | Backend likely not running: `docker compose logs backend` |
| Payment callback fails | `WECHAT_NOTIFY_URL` must be publicly accessible HTTPS |
| Gate won't open | Test with `GATE_TYPE=simulated` first, then check relay IP |
| DB locked | WAL mode prevents most locks; restart backend if needed |
