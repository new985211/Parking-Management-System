# Parking Lot LPR System — Production Deployment Guide

## Prerequisites

- Ubuntu 20.04+ / Kylin V10 (Debian-based)
- Docker 24+ & Docker Compose v2
- Python 3.11+ (for camera capture worker on host)
- Nginx (for SSL termination, optional if using Docker nginx)

## Quick Start (Development)

```bash
# 1. Start PaddleOCR service
cd docker/paddleocr
docker build -t parking-ocr .
docker run -d --name parking-ocr -p 5001:5001 parking-ocr

# 2. Start Flask backend
cd backend
pip install -r requirements.txt
python app.py
# → http://localhost:5000

# 3. Test OCR
curl -F "image=@test_plate.jpg" http://localhost:5001/ocr

# 4. Test full pipeline (simulated gate)
cd capture
python gate_worker.py --demo
```

## Production Deployment

### Option A: Docker Compose (Recommended)

```bash
# Clone and setup
cd parking-lpr

# Create data directory
mkdir -p data

# Configure environment
cp .env.example .env
# Edit .env with your settings:
#   SECRET_KEY=<random-string>
#   WECHAT_APP_ID=<your-wechat-app-id>
#   WECHAT_MCH_ID=<your-merchant-id>
#   WECHAT_API_KEY=<your-api-key>
#   GATE_RELAY_HOST=<relay-ip>

# Build and start all services
docker compose up -d --build

# Check status
docker compose ps
docker compose logs -f backend

# Visit: http://localhost
```

### Option B: Manual (Host-level)

```bash
# 1. PaddleOCR (Docker)
docker build -t parking-ocr docker/paddleocr/
docker run -d --name parking-ocr --restart always -p 5001:5001 parking-ocr

# 2. Flask Backend with Gunicorn
cd backend
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app --access-logfile /var/log/parking/access.log

# 3. Nginx
cp nginx/parking.conf /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/parking.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 4. Camera Worker (systemd)
cp capture/parking-capture.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now parking-capture
```

### Database

SQLite database is auto-created at first run. Default location: `backend/parking.db`

Backup:
```bash
# Daily backup via cron
0 3 * * * cp /path/to/parking-lpr/data/parking.db /backup/parking-$(date +\%Y\%m\%d).db
```

### Default Login

- URL: http://your-server/login
- Username: `admin`
- Password: `admin123`
- **Change after first login!**

## Camera Setup

### Hikvision RTSP
```
rtsp://admin:password@192.168.1.64:554/h264/ch1/main/av_stream
```

### Dahua RTSP
```
rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0
```

### Test with USB camera
```bash
GATE_TYPE=simulated python capture/gate_worker.py --demo
```

## WeChat Mini-Program Setup

1. Register at https://mp.weixin.qq.com
2. Get AppID and AppSecret
3. Set `WECHAT_APP_ID` and `WECHAT_APP_SECRET` in `.env`
4. Open `miniapp/` in WeChat DevTools
5. Update `app.js` → `apiBase` to your server URL
6. Upload and submit for review

## WeChat Pay Setup

1. Register merchant account at https://pay.weixin.qq.com
2. Get MCH ID, API Key, and certificates
3. Configure in `.env`:
   - `WECHAT_MCH_ID`
   - `WECHAT_API_KEY`
   - `WECHAT_NOTIFY_URL=https://your-domain.com/api/payment/callback`
4. Upload merchant certificate to server
5. In dev mode, payments are simulated (no real charges)

## Monitoring

```bash
# Service status
systemctl status parking-capture
docker compose ps

# Logs
docker compose logs -f backend
journalctl -u parking-capture -f

# Health check
curl http://localhost/health

# Database stats
sqlite3 data/parking.db "SELECT COUNT(*) FROM records WHERE DATE(created_at) = DATE('now')"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OCR returns empty | Check OCR container: `docker logs parking-ocr` |
| Camera won't connect | Verify RTSP URL with VLC, check firewall |
| Payment callback fails | Verify WECHAT_NOTIFY_URL is publicly accessible |
| Gate won't open | Check relay IP, try simulated mode first |
| DB locked | Restart backend (WAL mode prevents most locks) |
