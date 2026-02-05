---
description: ตรวจสอบและ Review การทำงานของโปรเจคก่อน Deploy (QA Checklist)
---

# Pre-Deploy QA Review Workflow

ขั้นตอนการตรวจสอบการทำงานของโปรเจคก่อน deploy เหมือนหัวหน้าตรวจงานก่อนอนุมัติ

## 1. ตรวจสอบ Code Quality

// turbo
```bash
cd "C:/Users/Administrator/OneDrive/01_FireControl/00_Ai_Project 7_Line Bot see fire"
python -m py_compile app/main.py app/services/scheduler_service.py app/services/notification_service.py app/services/firms_service.py
```

ถ้าไม่มี error แสดงว่า syntax ถูกต้อง

## 2. ตรวจสอบ Import Dependencies

// turbo
```bash
cd "C:/Users/Administrator/OneDrive/01_FireControl/00_Ai_Project 7_Line Bot see fire"
pip check
```

ตรวจสอบว่า dependencies ทั้งหมด compatible กัน

## 3. ตรวจสอบ Environment Variables

ต้องมี environment variables เหล่านี้ใน `.env` หรือ Railway:
- [ ] `FIRMS_MAP_KEY` - API Key จาก NASA FIRMS
- [ ] `LINE_CHANNEL_ACCESS_TOKEN` - LINE Bot Token
- [ ] `LINE_CHANNEL_SECRET` - LINE Bot Secret
- [ ] `LINE_GROUP_ID` - Group ID สำหรับส่งข้อความ
- [ ] `DATABASE_URL` - SQLite หรือ PostgreSQL URL
- [ ] `AREA_WEST`, `AREA_SOUTH`, `AREA_EAST`, `AREA_NORTH` - พิกัดพื้นที่

## 4. ทดสอบ FIRMS API

// turbo
```bash
cd "C:/Users/Administrator/OneDrive/01_FireControl/00_Ai_Project 7_Line Bot see fire"
python -c "import asyncio; from app.services.firms_service import FIRMSService; f = FIRMSService(); print('FIRMS Service OK')"
```

## 5. ตรวจสอบ Dashboard Web

เปิด browser ไปที่:
- **Local**: http://localhost:8000
- **Production**: https://erawan-firecheck-bot-production.up.railway.app/

ตรวจสอบ:
- [ ] หน้า Dashboard โหลดได้
- [ ] แสดงข้อมูล hotspots ถูกต้อง
- [ ] ปุ่ม "ตรวจสอบเดี๋ยวนี้" ทำงานได้

## 6. ตรวจสอบ LINE Bot Webhook

เปิด Railway logs หรือใช้คำสั่ง:

```bash
railway logs
```

ตรวจสอบ:
- [ ] ไม่มี error ใน logs
- [ ] Scheduler ทำงานตาม peak hours (01:30-06:00, 13:30-18:00)

## 7. ทดสอบส่งข้อความ LINE (Manual)

// turbo
```bash
cd "C:/Users/Administrator/OneDrive/01_FireControl/00_Ai_Project 7_Line Bot see fire"
python scripts/test_line.py
```

## 8. ตรวจสอบ Git Status

// turbo
```bash
cd "C:/Users/Administrator/OneDrive/01_FireControl/00_Ai_Project 7_Line Bot see fire"
git status
git log -n 5 --oneline
```

ตรวจสอบว่า:
- [ ] ไม่มี uncommitted changes
- [ ] Commit message ชัดเจน

## 9. ตรวจสอบ Railway Deployment

// turbo
```bash
railway status
```

หรือเปิด Railway Dashboard: https://railway.app/

ตรวจสอบ:
- [ ] Deployment สำเร็จ
- [ ] ไม่มี build errors
- [ ] Health check passed

---

## Summary Checklist

| หัวข้อ | Status |
|--------|--------|
| Code Syntax | ⬜ |
| Dependencies | ⬜ |
| Environment Variables | ⬜ |
| FIRMS API | ⬜ |
| Dashboard Web | ⬜ |
| LINE Webhook | ⬜ |
| LINE Message Test | ⬜ |
| Git Status | ⬜ |
| Railway Deploy | ⬜ |

เมื่อทุกหัวข้อผ่านแล้ว (✅) ถือว่าพร้อม deploy!
