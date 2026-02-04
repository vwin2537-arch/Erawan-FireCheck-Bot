# 🤖 Claude Code Prompts - FIRMS LINE Bot

ใช้ prompts เหล่านี้ตามลำดับกับ Claude Code เพื่อสร้างโปรเจค

---

## 🚀 Prompt 1: Initial Setup

```
สร้างโปรเจค Python FastAPI ชื่อ "firms-line-bot" สำหรับระบบแจ้งเตือนจุดความร้อน (Hotspot) ผ่าน LINE

โครงสร้างโปรเจค:
firms-line-bot/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firms_service.py
│   │   ├── line_service.py
│   │   ├── notification_service.py
│   │   └── scheduler_service.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhook.py
│   │   ├── dashboard.py
│   │   └── health.py
│   └── utils/
│       ├── __init__.py
│       └── message_formatter.py
├── templates/
│   └── dashboard.html
├── scripts/
│   ├── init_db.py
│   └── test_line_push.py
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
└── README.md

requirements.txt:
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
httpx>=0.26.0
python-dotenv>=1.0.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
apscheduler>=3.10.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
jinja2>=3.1.0
python-multipart>=0.0.6
line-bot-sdk>=3.5.0

.env.example:
APP_NAME=FIRMS LINE Bot
DEBUG=true
FIRMS_MAP_KEY=your-firms-map-key
LINE_CHANNEL_ACCESS_TOKEN=your-token
LINE_CHANNEL_SECRET=your-secret
LINE_GROUP_ID=your-group-id
DATABASE_URL=sqlite:///./data/firms_bot.db
TIMEZONE=Asia/Bangkok

สร้าง app/config.py ใช้ pydantic-settings สำหรับอ่าน environment variables
```

---

## 🗄️ Prompt 2: Database Models

```
สร้าง database layer สำหรับ firms-line-bot:

1. app/database.py - SQLAlchemy async setup:
   - ใช้ aiosqlite สำหรับ SQLite
   - create_async_engine
   - async_sessionmaker
   - get_db dependency

2. app/models.py - SQLAlchemy models:

   class Hotspot(Base):
       id: int (PK, autoincrement)
       latitude: float
       longitude: float
       brightness: float (nullable)
       acq_date: date
       acq_time: time
       satellite: str  # VIIRS_SNPP, VIIRS_NOAA20, VIIRS_NOAA21
       confidence: str  # low, nominal, high
       frp: float (nullable)  # Fire Radiative Power
       daynight: str  # D or N
       province: str (nullable)
       district: str (nullable)
       notified: bool (default False)
       notified_at: datetime (nullable)
       created_at: datetime (default now)
       
       # UNIQUE constraint: (latitude, longitude, acq_date, acq_time, satellite)

   class Notification(Base):
       id: int (PK)
       batch_id: str (UUID)
       hotspot_count: int
       message_text: str
       sent_at: datetime
       status: str  # sent, failed, pending
       error_message: str (nullable)

   class CheckLog(Base):
       id: int (PK)
       checked_at: datetime
       hotspots_found: int
       new_hotspots: int
       status: str  # success, error
       error_message: str (nullable)

3. app/schemas.py - Pydantic schemas สำหรับ API

4. scripts/init_db.py - Script สร้าง tables

ใช้ SQLAlchemy 2.0 async style
```

---

## 🛰️ Prompt 3: FIRMS Service

```
สร้าง app/services/firms_service.py สำหรับดึงข้อมูลจาก NASA FIRMS API:

class FIRMSService:
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    
    SOURCES = [
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT", 
        "VIIRS_NOAA21_NRT"
    ]
    
    # Thailand bounding box
    DEFAULT_AREA = {
        "west": 97.5,
        "south": 5.5,
        "east": 105.6,
        "north": 20.5
    }

Methods:
1. async get_hotspots(source: str, area: dict, day_range: int = 1) -> list[dict]
   - URL: {BASE_URL}/{MAP_KEY}/{source}/{west},{south},{east},{north}/{day_range}
   - Parse CSV response เป็น list of dictionaries
   - Handle errors gracefully
   
2. async get_all_sources(area: dict = None, day_range: int = 1) -> list[dict]
   - ดึงจากทุก source ใน SOURCES
   - รวม results ทั้งหมด
   - ลบ duplicates ถ้ามี

3. parse_csv_response(csv_text: str) -> list[dict]
   - Parse CSV string เป็น list of dicts
   - Convert types: float สำหรับ lat/lon/brightness, date/time สำหรับ acq_date/acq_time

ใช้ httpx สำหรับ async HTTP requests
เพิ่ม logging สำหรับ debug
Timeout: 30 seconds
Retry: 3 times with exponential backoff
```

---

## 📱 Prompt 4: LINE Service

```
สร้าง app/services/line_service.py สำหรับส่งแจ้งเตือนผ่าน LINE:

class LINEService:
    def __init__(self, channel_access_token: str, channel_secret: str):
        # Initialize LINE Bot API

Methods:
1. async push_message(to: str, messages: list) -> dict
   - ส่ง push message ไปยัง group ID
   - Return response จาก LINE API

2. async send_hotspot_alert(group_id: str, hotspots: list, summary: dict) -> dict
   - สร้าง Flex Message สำหรับแจ้งเตือน
   - เรียก push_message

3. create_flex_message(hotspots: list, summary: dict) -> dict
   - สร้าง LINE Flex Message bubble
   
   Format ข้อความ:
   🔥 แจ้งเตือนจุดความร้อน
   ━━━━━━━━━━━━━━━━━
   📍 พบ {total} จุด
   
   🏔️ {province} ({count} จุด)
   • {district} - {count} จุด
   
   🛰️ ดาวเทียม: {satellite}
   🕐 เวลาถ่าย: {time}
   
   [ปุ่ม: 🗺️ ดูแผนที่]

4. async send_test_message(group_id: str) -> dict
   - ส่งข้อความทดสอบ

ใช้ line-bot-sdk v3 (from linebot.v3)
Handle LineBotApiError
```

---

## 🔔 Prompt 5: Notification Service

```
สร้าง app/services/notification_service.py - Core notification logic:

class NotificationService:
    def __init__(self, firms: FIRMSService, line: LINEService, db_session):
        self.firms = firms
        self.line = line  
        self.db = db_session

Methods:
1. async check_and_notify() -> dict
   Main routine:
   a) ดึง hotspots จาก FIRMS API (all sources)
   b) Query database หา hotspot ที่มีอยู่แล้ว
   c) Filter เอาเฉพาะ hotspot ใหม่ (เทียบ lat, lon, acq_date, acq_time, satellite)
   d) ถ้ามี hotspot ใหม่:
      - บันทึกลง database
      - สร้าง summary จัดกลุ่มตาม province/district
      - ส่ง LINE notification
      - บันทึก notification record
   e) บันทึก check log
   f) Return summary

2. filter_new_hotspots(hotspots: list, existing: list) -> list
   - เปรียบเทียบหา hotspot ที่ยังไม่มีใน database
   - ใช้ (lat, lon, acq_date, acq_time, satellite) เป็น key

3. group_hotspots_by_location(hotspots: list) -> dict
   - จัดกลุ่มตาม province -> district
   - Return: {"เชียงใหม่": {"แม่แจ่ม": [...], "อมก๋อย": [...]}}
   - ถ้าไม่มี province ให้ใช้ "ไม่ระบุ"

4. create_summary(hotspots: list, grouped: dict) -> dict
   - Return: {
       "total": int,
       "by_province": {"เชียงใหม่": 5, ...},
       "satellites": ["VIIRS_NOAA20"],
       "latest_acq_time": "14:35",
       "confidence_high": 3,
       "confidence_nominal": 2
     }

5. async save_hotspots(hotspots: list) -> int
   - Bulk insert hotspots to database
   - Return count of inserted records

6. async save_check_log(found: int, new: int, status: str, error: str = None)
   - บันทึก log การ check
```

---

## ⏰ Prompt 6: Scheduler Service

```
สร้าง app/services/scheduler_service.py - Adaptive scheduler:

ข้อมูลเวลาดาวเทียมผ่านประเทศไทย:
- Suomi NPP:  ~01:30 / ~13:30 น.
- NOAA-20:    ~02:20 / ~14:20 น.
- NOAA-21:    ~03:10 / ~15:10 น.
- ข้อมูลพร้อมใช้: +60 ถึง +125 นาที หลังดาวเทียมผ่าน

Schedule Strategy:
- Peak hours: เช็คทุก 10 นาที
  - 02:30 - 06:00 (รอข้อมูลจากรอบกลางคืน)
  - 14:30 - 18:00 (รอข้อมูลจากรอบกลางวัน)
- Off-peak: เช็คทุก 30 นาที

class SchedulerService:
    PEAK_WINDOWS = [
        {"start": (2, 30), "end": (6, 0)},   # 02:30 - 06:00
        {"start": (14, 30), "end": (18, 0)}  # 14:30 - 18:00
    ]
    
    PEAK_INTERVAL = 10  # minutes
    OFFPEAK_INTERVAL = 30  # minutes

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler(timezone="Asia/Bangkok")
        self.last_check = None

Methods:
1. start()
   - เพิ่ม job ที่รันทุกนาที
   - scheduler.start()

2. stop()
   - scheduler.shutdown()

3. async check_job()
   - เรียกทุกนาที
   - ตรวจสอบว่าถึงเวลา check หรือยัง (ตาม peak/offpeak interval)
   - ถ้าถึงเวลา: เรียก notification_service.check_and_notify()

4. is_peak_time(dt: datetime) -> bool
   - ตรวจสอบว่าอยู่ใน peak window หรือไม่

5. should_check_now(dt: datetime) -> bool
   - Peak: minute % 10 == 0
   - Off-peak: minute % 30 == 0

6. async manual_check() -> dict
   - สำหรับ trigger check แบบ manual
   - เรียก notification_service.check_and_notify() ทันที

ใช้ APScheduler AsyncIOScheduler
Timezone: Asia/Bangkok (ZoneInfo)
```

---

## 🌐 Prompt 7: API Routes

```
สร้าง API routes:

1. app/routers/health.py:
   GET /health -> {"status": "ok", "timestamp": "..."}
   GET /status -> {
       "is_running": true,
       "scheduler_active": true,
       "last_check": "2024-02-04T14:30:00",
       "next_check_estimate": "2024-02-04T14:40:00",
       "total_hotspots_today": 15,
       "notifications_today": 3
   }

2. app/routers/dashboard.py:
   GET /dashboard -> HTML dashboard page
   GET /api/hotspots?date=2024-02-04&province=เชียงใหม่ -> list of hotspots
   GET /api/hotspots/today -> today's hotspots
   GET /api/hotspots/stats -> {
       "today": 15,
       "week": 89,
       "by_province": {...},
       "by_satellite": {...}
   }
   GET /api/notifications?limit=20 -> notification history
   GET /api/logs?limit=50 -> check logs
   POST /api/check-now -> trigger immediate check, return result
   POST /api/test-notification -> send test notification

3. app/routers/webhook.py:
   POST /webhook -> LINE webhook handler
   - Verify signature
   - Handle events (optional: reply to commands)

ใช้ Depends สำหรับ database session
Return proper HTTP status codes
Add request validation
```

---

## 🏠 Prompt 8: Main Application

```
สร้าง app/main.py - FastAPI application:

from fastapi import FastAPI
from contextlib import asynccontextmanager

Features:
1. Lifespan handler:
   - startup: initialize database, start scheduler
   - shutdown: stop scheduler

2. Include routers:
   - health router (prefix: "")
   - dashboard router (prefix: "")
   - webhook router (prefix: "")

3. CORS middleware (allow all origins for development)

4. Static files mount (/static)

5. Templates setup (Jinja2)

6. Exception handlers

7. Dependency injection:
   - get_firms_service
   - get_line_service  
   - get_notification_service
   - get_scheduler_service

สร้าง templates/dashboard.html:
- Simple HTML dashboard
- แสดง status, last check time
- ตาราง hotspot วันนี้
- ปุ่ม "Check Now" และ "Test Notification"
- Auto refresh ทุก 60 วินาที
- ใช้ Tailwind CSS CDN สำหรับ styling
```

---

## 🧪 Prompt 9: Test Scripts

```
สร้าง scripts สำหรับทดสอบ:

1. scripts/test_firms_api.py:
   - ทดสอบดึงข้อมูลจาก FIRMS API
   - แสดง sample hotspots
   - Print statistics
   
   Usage: python scripts/test_firms_api.py

2. scripts/test_line_push.py:
   - ทดสอบส่ง push message ไป LINE
   - ส่งข้อความทดสอบง่ายๆ
   - ส่ง sample hotspot alert
   
   Usage: python scripts/test_line_push.py

3. scripts/init_db.py:
   - สร้าง database tables
   - Insert default settings ถ้าต้องการ
   
   Usage: python scripts/init_db.py

ทุก script อ่าน .env file
มี error handling ที่ดี
แสดง output ที่เข้าใจง่าย
```

---

## 📦 Prompt 10: Deployment Files

```
สร้างไฟล์สำหรับ deployment:

1. Dockerfile:
   - Base: python:3.11-slim
   - Set timezone Asia/Bangkok
   - Install requirements
   - Create /app/data directory for SQLite
   - CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000

2. docker-compose.yml:
   - Service: app
   - Build from Dockerfile
   - Ports: 8000:8000
   - Volumes: ./data:/app/data
   - env_file: .env

3. railway.json (สำหรับ Railway deployment):
   {
     "build": {"builder": "DOCKERFILE"},
     "deploy": {
       "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
       "healthcheckPath": "/health"
     }
   }

4. README.md:
   - Project description
   - Features
   - Prerequisites
   - Setup instructions (FIRMS API key, LINE setup)
   - Environment variables
   - Running locally
   - Deployment guide
   - API documentation
   - Troubleshooting
```

---

## 🎯 Quick Start Prompt (All-in-One)

ถ้าต้องการให้ Claude Code สร้างทั้งหมดในครั้งเดียว:

```
สร้างระบบ LINE Bot แจ้งเตือนจุดความร้อน (Hotspot) จาก NASA FIRMS API

Tech Stack:
- Python 3.11 + FastAPI
- SQLite + SQLAlchemy (async)
- APScheduler
- LINE Messaging API (line-bot-sdk v3)
- httpx for HTTP requests

Features:
1. ดึงข้อมูล Hotspot จาก NASA FIRMS API (VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, VIIRS_NOAA21_NRT)
2. ตรวจจับ hotspot ใหม่โดยเทียบกับ database (ใช้ lat, lon, acq_date, acq_time, satellite)
3. ส่งแจ้งเตือนผ่าน LINE Flex Message เมื่อพบ hotspot ใหม่
4. Adaptive scheduler:
   - Peak hours (02:30-06:00, 14:30-18:00): เช็คทุก 10 นาที
   - Off-peak: เช็คทุก 30 นาที
5. Web dashboard แสดง status และประวัติ
6. API endpoints สำหรับ manual check และดูข้อมูล

Thailand bounding box: 97.5,5.5,105.6,20.5 (west,south,east,north)
Timezone: Asia/Bangkok

Database tables:
- hotspots (เก็บ hotspot ที่ตรวจพบ)
- notifications (ประวัติการแจ้งเตือน)
- check_logs (log การ check)

สร้างโปรเจคที่สมบูรณ์พร้อม:
- ทุก files ตาม structure
- Dockerfile และ docker-compose.yml
- README.md
- Test scripts
- .env.example
```

---

## 📝 Notes

1. **ลำดับการสร้าง**: ทำตาม Prompt 1-10 ตามลำดับ หรือใช้ Quick Start Prompt
2. **ทดสอบ**: หลังแต่ละ prompt ควรทดสอบว่าทำงานได้
3. **API Keys**: ต้องมี FIRMS MAP_KEY และ LINE credentials ก่อนทดสอบจริง
4. **Debug**: ใช้ DEBUG=true ใน .env เพื่อดู logs
