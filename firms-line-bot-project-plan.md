# 🔥 FIRMS LINE Bot - แผนโปรเจคสำหรับ Claude Code

## 📋 Project Overview

### ชื่อโปรเจค
**FIRMS LINE Bot** - ระบบแจ้งเตือนจุดความร้อน (Hotspot) ผ่าน LINE

### วัตถุประสงค์
สร้างระบบอัตโนมัติที่ตรวจจับข้อมูล Hotspot ใหม่จาก NASA FIRMS API และส่งแจ้งเตือนไปยัง LINE Group ของเจ้าหน้าที่ดับไฟป่า

### Core Features
1. ดึงข้อมูล Hotspot จาก NASA FIRMS API
2. ตรวจจับข้อมูลใหม่ (เทียบกับ acquisition time)
3. ส่งแจ้งเตือนผ่าน LINE Messaging API
4. Scheduler ที่ปรับความถี่ตามช่วงเวลา
5. Web Dashboard สำหรับดูสถานะและประวัติ

---

## 🛠️ Tech Stack

```
Backend:        Python 3.11+ with FastAPI
Database:       SQLite (development) / PostgreSQL (production)
Scheduler:      APScheduler
LINE API:       LINE Messaging API (Push Message)
Deployment:     Railway / Render / VPS
```

---

## 📁 Project Structure

```
firms-line-bot/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration & env variables
│   ├── database.py             # Database connection & models
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firms_service.py    # NASA FIRMS API integration
│   │   ├── line_service.py     # LINE Messaging API integration
│   │   ├── notification_service.py  # Notification logic
│   │   └── scheduler_service.py     # Job scheduling
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhook.py          # LINE webhook endpoint
│   │   ├── dashboard.py        # Dashboard API endpoints
│   │   └── health.py           # Health check endpoint
│   │
│   └── utils/
│       ├── __init__.py
│       ├── geo_utils.py        # Geographic calculations
│       ├── time_utils.py       # Time zone handling
│       └── message_formatter.py # LINE message formatting
│
├── templates/
│   └── dashboard.html          # Simple dashboard UI
│
├── static/
│   └── style.css
│
├── tests/
│   ├── __init__.py
│   ├── test_firms_service.py
│   ├── test_line_service.py
│   └── test_notification.py
│
├── scripts/
│   ├── init_db.py              # Database initialization
│   └── test_line_push.py       # Test LINE push message
│
├── .env.example                # Environment variables template
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── railway.json                # Railway deployment config
└── README.md
```

---

## 🗄️ Database Schema

### Table: hotspots
เก็บประวัติ Hotspot ที่ตรวจพบ

```sql
CREATE TABLE hotspots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    brightness REAL,
    scan REAL,
    track REAL,
    acq_date DATE NOT NULL,
    acq_time TIME NOT NULL,
    satellite TEXT NOT NULL,          -- 'VIIRS_SNPP', 'VIIRS_NOAA20', 'VIIRS_NOAA21'
    instrument TEXT,
    confidence TEXT,                  -- 'low', 'nominal', 'high'
    version TEXT,
    bright_t31 REAL,
    frp REAL,                         -- Fire Radiative Power
    daynight TEXT,                    -- 'D' or 'N'
    
    -- Additional fields
    province TEXT,                    -- จังหวัด (mapped from coordinates)
    district TEXT,                    -- อำเภอ
    land_type TEXT,                   -- ประเภทพื้นที่
    
    -- Metadata
    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicates
    UNIQUE(latitude, longitude, acq_date, acq_time, satellite)
);
```

### Table: notifications
เก็บประวัติการแจ้งเตือน

```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,           -- UUID for grouping
    hotspot_count INTEGER NOT NULL,
    message_text TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',       -- 'sent', 'failed', 'pending'
    error_message TEXT,
    line_response TEXT                -- JSON response from LINE API
);
```

### Table: check_logs
เก็บ log การเช็ค API

```sql
CREATE TABLE check_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hotspots_found INTEGER DEFAULT 0,
    new_hotspots INTEGER DEFAULT 0,
    api_response_time_ms INTEGER,
    status TEXT DEFAULT 'success',    -- 'success', 'error'
    error_message TEXT
);
```

### Table: settings
เก็บการตั้งค่าระบบ

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default settings
INSERT INTO settings (key, value) VALUES
    ('monitoring_area', '{"west": 97.5, "south": 5.5, "east": 105.6, "north": 20.5}'),
    ('check_interval_peak', '10'),      -- minutes
    ('check_interval_offpeak', '30'),   -- minutes
    ('min_confidence', 'nominal'),      -- 'low', 'nominal', 'high'
    ('line_group_id', ''),
    ('is_active', 'true');
```

---

## 🔌 API Endpoints

### Health & Status
```
GET  /health                    # Health check
GET  /status                    # System status & last check info
```

### Dashboard
```
GET  /dashboard                 # Dashboard HTML page
GET  /api/hotspots              # Get hotspots (with filters)
GET  /api/hotspots/today        # Today's hotspots
GET  /api/hotspots/stats        # Statistics
GET  /api/notifications         # Notification history
GET  /api/logs                  # Check logs
```

### Manual Actions
```
POST /api/check-now             # Trigger immediate check
POST /api/test-notification     # Send test notification
POST /api/settings              # Update settings
```

### LINE Webhook
```
POST /webhook                   # LINE webhook endpoint
```

---

## ⚙️ Core Services

### 1. FIRMS Service (`firms_service.py`)

```python
"""
NASA FIRMS API Integration

API Documentation: https://firms.modaps.eosdis.nasa.gov/api/area/

Endpoints:
- Area: https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}

Sources:
- VIIRS_SNPP_NRT
- VIIRS_NOAA20_NRT  
- VIIRS_NOAA21_NRT
- MODIS_NRT

Area format: west,south,east,north (bounding box)
Thailand: 97.5,5.5,105.6,20.5
"""

class FIRMSService:
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    
    def __init__(self, map_key: str):
        self.map_key = map_key
        
    async def get_hotspots(
        self,
        source: str = "VIIRS_SNPP_NRT",
        area: dict = None,  # {"west": 97.5, "south": 5.5, "east": 105.6, "north": 20.5}
        day_range: int = 1
    ) -> list[dict]:
        """
        Fetch hotspots from FIRMS API
        
        Returns list of hotspot dictionaries with fields:
        - latitude, longitude
        - brightness, bright_t31
        - scan, track
        - acq_date, acq_time (acquisition date/time)
        - satellite, instrument
        - confidence (low/nominal/high)
        - version (NRT/RT/URT)
        - frp (Fire Radiative Power)
        - daynight (D/N)
        """
        pass
    
    async def get_all_sources(self, area: dict, day_range: int = 1) -> list[dict]:
        """Fetch from all VIIRS sources and combine"""
        sources = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
        # Fetch all and merge
        pass
```

### 2. LINE Service (`line_service.py`)

```python
"""
LINE Messaging API Integration

Documentation: https://developers.line.biz/en/docs/messaging-api/

Required:
- Channel Access Token
- Group ID (for push messages)
"""

class LINEService:
    BASE_URL = "https://api.line.me/v2/bot"
    
    def __init__(self, channel_access_token: str):
        self.token = channel_access_token
        
    async def push_message(
        self,
        to: str,  # Group ID or User ID
        messages: list[dict]
    ) -> dict:
        """
        Send push message to LINE
        
        Message types:
        - text: {"type": "text", "text": "..."}
        - flex: {"type": "flex", "altText": "...", "contents": {...}}
        - location: {"type": "location", "title": "...", "address": "...", "latitude": ..., "longitude": ...}
        """
        pass
    
    async def send_hotspot_alert(
        self,
        group_id: str,
        hotspots: list[dict],
        summary: dict
    ) -> dict:
        """Send formatted hotspot alert"""
        pass
```

### 3. Notification Service (`notification_service.py`)

```python
"""
Core notification logic
"""

class NotificationService:
    def __init__(
        self,
        firms_service: FIRMSService,
        line_service: LINEService,
        db: Database
    ):
        self.firms = firms_service
        self.line = line_service
        self.db = db
        
    async def check_and_notify(self) -> dict:
        """
        Main check routine:
        1. Fetch hotspots from FIRMS
        2. Compare with database (find new ones by acq_time)
        3. Save new hotspots to database
        4. If new hotspots found, send LINE notification
        5. Log the check
        
        Returns: {
            "checked_at": datetime,
            "hotspots_found": int,
            "new_hotspots": int,
            "notification_sent": bool
        }
        """
        pass
    
    def filter_new_hotspots(
        self,
        hotspots: list[dict],
        last_check_time: datetime
    ) -> list[dict]:
        """
        Filter hotspots that are newer than last check
        Use acq_date + acq_time for comparison
        """
        pass
    
    def group_by_location(
        self,
        hotspots: list[dict]
    ) -> dict:
        """
        Group hotspots by province/district for summary
        Returns: {
            "เชียงใหม่": {
                "แม่แจ่ม": [hotspot1, hotspot2],
                "อมก๋อย": [hotspot3]
            }
        }
        """
        pass
```

### 4. Scheduler Service (`scheduler_service.py`)

```python
"""
Adaptive scheduling based on satellite overpass times

Thailand satellite overpass times (local time):
- Suomi NPP:  ~01:30 / ~13:30
- NOAA-20:    ~02:20 / ~14:20
- NOAA-21:    ~03:10 / ~15:10

Data available: +60 to +125 minutes after overpass

Peak check windows:
- Night: 02:30 - 06:00
- Day:   14:30 - 18:00
"""

class SchedulerService:
    # Peak hours (check every 10 minutes)
    PEAK_HOURS = [
        (2, 30, 6, 0),    # 02:30 - 06:00
        (14, 30, 18, 0),  # 14:30 - 18:00
    ]
    
    # Off-peak: check every 30 minutes
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler(timezone="Asia/Bangkok")
        
    def start(self):
        """Start the scheduler with adaptive intervals"""
        # Add job that runs every minute and decides whether to check
        self.scheduler.add_job(
            self.adaptive_check,
            'cron',
            minute='*',
            id='adaptive_check'
        )
        self.scheduler.start()
        
    async def adaptive_check(self):
        """
        Called every minute, decides whether to actually check
        based on current time
        """
        now = datetime.now(tz=ZoneInfo("Asia/Bangkok"))
        
        if self.is_peak_time(now):
            # Peak: check every 10 minutes
            if now.minute % 10 == 0:
                await self.notification_service.check_and_notify()
        else:
            # Off-peak: check every 30 minutes
            if now.minute % 30 == 0:
                await self.notification_service.check_and_notify()
                
    def is_peak_time(self, dt: datetime) -> bool:
        """Check if current time is within peak hours"""
        pass
```

---

## 📝 Message Format

### LINE Flex Message Template

```python
def create_hotspot_alert_message(hotspots: list, summary: dict) -> dict:
    """
    Create LINE Flex Message for hotspot alert
    
    Example output message:
    
    🔥 แจ้งเตือนจุดความร้อน
    ━━━━━━━━━━━━━━━━━
    📍 พบ 8 จุด ในพื้นที่รับผิดชอบ
    
    🏔️ เชียงใหม่ (5 จุด)
    • แม่แจ่ม - 3 จุด
    • อมก๋อย - 2 จุด
    
    🏔️ ลำปาง (3 จุด)  
    • แจ้ห่ม - 3 จุด
    
    🛰️ ดาวเทียม: VIIRS NOAA-20
    🕐 เวลาถ่าย: 14:35 น.
    📊 ความเชื่อมั่น: สูง
    
    🗺️ ดูแผนที่: [link]
    """
    
    return {
        "type": "flex",
        "altText": f"🔥 แจ้งเตือนจุดความร้อน {summary['total']} จุด",
        "contents": {
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🔥 แจ้งเตือนจุดความร้อน",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#FF5555"
                    }
                ],
                "backgroundColor": "#FFF5F5"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # ... dynamic content based on hotspots
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical", 
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ ดูแผนที่",
                            "uri": "https://firms.modaps.eosdis.nasa.gov/map/"
                        },
                        "style": "primary",
                        "color": "#FF5555"
                    }
                ]
            }
        }
    }
```

---

## 🔐 Environment Variables

### `.env.example`

```env
# ===================
# App Configuration
# ===================
APP_NAME=FIRMS LINE Bot
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# ===================
# NASA FIRMS API
# ===================
# Get your key at: https://firms.modaps.eosdis.nasa.gov/api/map_key/
FIRMS_MAP_KEY=your-firms-map-key

# ===================
# LINE Messaging API
# ===================
# Get from LINE Developers Console
LINE_CHANNEL_ACCESS_TOKEN=your-line-channel-access-token
LINE_CHANNEL_SECRET=your-line-channel-secret
LINE_GROUP_ID=your-target-group-id

# ===================
# Database
# ===================
DATABASE_URL=sqlite:///./firms_bot.db
# For production PostgreSQL:
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# ===================
# Monitoring Area (Thailand)
# ===================
AREA_WEST=97.5
AREA_SOUTH=5.5
AREA_EAST=105.6
AREA_NORTH=20.5

# ===================
# Scheduler Settings
# ===================
TIMEZONE=Asia/Bangkok
CHECK_INTERVAL_PEAK=10
CHECK_INTERVAL_OFFPEAK=30

# ===================
# Notification Settings
# ===================
MIN_CONFIDENCE=nominal
NOTIFY_ON_STARTUP=false
```

---

## 🚀 Deployment

### Railway Deployment

```json
// railway.json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Set timezone
ENV TZ=Asia/Bangkok
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### requirements.txt

```
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
```

---

## 📖 Step-by-Step Prompts for Claude Code

ใช้ prompts เหล่านี้ตามลำดับเพื่อสร้างโปรเจค:

### Prompt 1: Project Setup

```
สร้างโปรเจค Python FastAPI ชื่อ "firms-line-bot" ตามโครงสร้างนี้:

[วาง Project Structure จากด้านบน]

สร้างไฟล์พื้นฐาน:
- requirements.txt ตามที่ระบุ
- .env.example
- .gitignore (Python + environment files)
- app/__init__.py
- app/config.py (ใช้ pydantic-settings อ่าน env)
```

### Prompt 2: Database Setup

```
สร้าง database layer สำหรับ firms-line-bot:

1. app/database.py - SQLAlchemy async setup with aiosqlite
2. app/models.py - SQLAlchemy models ตาม schema นี้:

[วาง Database Schema จากด้านบน]

3. scripts/init_db.py - Script สำหรับ initialize database

ใช้ SQLAlchemy 2.0 style กับ async session
```

### Prompt 3: FIRMS Service

```
สร้าง app/services/firms_service.py สำหรับดึงข้อมูลจาก NASA FIRMS API:

API Endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}

Sources ที่ต้องรองรับ:
- VIIRS_SNPP_NRT
- VIIRS_NOAA20_NRT
- VIIRS_NOAA21_NRT

Features:
1. get_hotspots() - ดึงจาก source เดียว
2. get_all_sources() - ดึงจากทุก source แล้วรวมกัน
3. parse CSV response เป็น list of dict
4. Error handling และ retry logic
5. Logging

Area สำหรับประเทศไทย: 97.5,5.5,105.6,20.5 (west,south,east,north)
```

### Prompt 4: LINE Service

```
สร้าง app/services/line_service.py สำหรับส่งข้อความผ่าน LINE Messaging API:

Features:
1. push_message() - ส่ง push message ไปยัง group
2. send_hotspot_alert() - ส่งแจ้งเตือน hotspot แบบ Flex Message
3. create_flex_message() - สร้าง Flex Message template สำหรับแจ้งเตือน

Flex Message ต้องแสดง:
- จำนวน hotspot ทั้งหมด
- แยกตามจังหวัด/อำเภอ
- ข้อมูลดาวเทียมและเวลาถ่ายภาพ
- ปุ่มลิงก์ไปดูแผนที่

ใช้ line-bot-sdk version 3
```

### Prompt 5: Notification Service

```
สร้าง app/services/notification_service.py - Core logic สำหรับตรวจจับและแจ้งเตือน:

Features:
1. check_and_notify() - Main routine:
   - ดึง hotspots จาก FIRMS
   - เปรียบเทียบกับ database หา hotspot ใหม่ (ใช้ acq_date + acq_time)
   - บันทึกลง database
   - ถ้ามี hotspot ใหม่ ส่ง LINE notification
   - บันทึก log

2. filter_new_hotspots() - กรอง hotspot ใหม่

3. group_by_location() - จัดกลุ่มตามพื้นที่

4. create_summary() - สร้างสรุปสำหรับแจ้งเตือน

Inject dependencies: FIRMSService, LINEService, Database
```

### Prompt 6: Scheduler Service

```
สร้าง app/services/scheduler_service.py - Adaptive scheduler:

Thailand satellite overpass times:
- Suomi NPP:  ~01:30 / ~13:30
- NOAA-20:    ~02:20 / ~14:20  
- NOAA-21:    ~03:10 / ~15:10

Data available: +60 to +125 minutes after overpass

Schedule:
- Peak hours (02:30-06:00, 14:30-18:00): เช็คทุก 10 นาที
- Off-peak: เช็คทุก 30 นาที

ใช้ APScheduler กับ AsyncIOScheduler
Timezone: Asia/Bangkok
```

### Prompt 7: API Routes

```
สร้าง API routes สำหรับ firms-line-bot:

1. app/routers/health.py
   - GET /health - health check
   - GET /status - system status

2. app/routers/dashboard.py
   - GET /api/hotspots - list hotspots (with date filter)
   - GET /api/hotspots/today - today's hotspots
   - GET /api/notifications - notification history
   - GET /api/logs - check logs
   - POST /api/check-now - trigger immediate check
   - POST /api/test-notification - send test notification

3. app/routers/webhook.py
   - POST /webhook - LINE webhook endpoint
```

### Prompt 8: Main Application

```
สร้าง app/main.py - FastAPI application entry point:

Features:
1. Initialize FastAPI app
2. Include all routers
3. Setup CORS
4. Initialize database on startup
5. Start scheduler on startup
6. Shutdown scheduler on shutdown
7. Dependency injection setup

เพิ่ม simple dashboard HTML template ที่ templates/dashboard.html
แสดง status และ hotspot ล่าสุด
```

### Prompt 9: Testing

```
สร้าง test scripts:

1. scripts/test_firms_api.py
   - ทดสอบการดึงข้อมูลจาก FIRMS API
   - แสดง sample data

2. scripts/test_line_push.py  
   - ทดสอบส่ง push message ไป LINE
   - ส่งข้อความทดสอบ

3. tests/test_notification_service.py
   - Unit tests สำหรับ notification logic
```

### Prompt 10: Documentation

```
สร้าง README.md ที่ครอบคลุม:

1. Project overview
2. Features
3. Prerequisites (FIRMS API key, LINE account setup)
4. Installation steps
5. Configuration (.env)
6. Running locally
7. Deployment (Railway)
8. API documentation
9. Troubleshooting
```

---

## 🔗 Important Links

- NASA FIRMS API: https://firms.modaps.eosdis.nasa.gov/api/
- FIRMS Map Key: https://firms.modaps.eosdis.nasa.gov/api/map_key/
- LINE Developers: https://developers.line.biz/
- LINE Messaging API: https://developers.line.biz/en/docs/messaging-api/
- Satellite Overpass Predictor: https://eogdata.mines.edu/predict/

---

## ⚠️ Important Notes

1. **FIRMS API Key**: ฟรี แต่มี limit 5,000 transactions / 10 นาที
2. **LINE Group ID**: ต้องเชิญ Bot เข้า Group ก่อนถึงจะส่ง push ได้
3. **Timezone**: ทุกอย่างใช้ Asia/Bangkok
4. **Acquisition Time**: ใช้ acq_date + acq_time ในการตรวจจับข้อมูลใหม่ ไม่ใช่เวลาที่ดึง API
5. **Duplicate Prevention**: ใช้ UNIQUE constraint บน (lat, lon, acq_date, acq_time, satellite)
