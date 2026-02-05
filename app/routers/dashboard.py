from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from typing import List
from ..database import get_db
from ..config import get_settings
from ..models import Hotspot, Notification, CheckLog, Setting
from ..services.notification_service import NotificationService
from ..services.firms_service import FIRMSService
from ..services.line_service import LINEService
from pydantic import BaseModel
from datetime import datetime, date, timezone, timedelta

router = APIRouter(prefix="/api", tags=["Dashboard"])

# Thai timezone (UTC+7)
THAI_TZ = timezone(timedelta(hours=7))

class SettingUpdate(BaseModel):
    key: str
    value: str

@router.get("/hotspots")
async def get_hotspots(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(Hotspot).order_by(desc(Hotspot.created_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/hotspots/today")
async def get_hotspots_today(db: AsyncSession = Depends(get_db)):
    # Use Thai timezone to get today's date
    thai_now = datetime.now(THAI_TZ)
    today = thai_now.date()
    yesterday = today - timedelta(days=1)
    
    # Get hotspots from today AND yesterday
    stmt = select(Hotspot).where(
        or_(Hotspot.acq_date == today, Hotspot.acq_date == yesterday)
    ).order_by(desc(Hotspot.acq_date), desc(Hotspot.acq_time))
    
    result = await db.execute(stmt)
    hotspots_raw = result.scalars().all()
    
    # Standardize time format for JS to display easily
    hotspots = []
    for h in hotspots_raw:
        # Robust time string extraction
        if hasattr(h.acq_time, "strftime"):
            time_display = h.acq_time.strftime("%H:%M")
        else:
            ts = str(h.acq_time or "")
            if len(ts) == 4 and ":" not in ts:
                time_display = f"{ts[:2]}:{ts[2:]}"
            else:
                time_display = ts[:5]
        
        hotspots.append({
            "id": h.id,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "acq_date": str(h.acq_date),
            "acq_time": time_display,
            "satellite": h.satellite,
            "confidence": h.confidence,
            "frp": h.frp
        })
    
    # Calculate today's count strictly for the summary card
    today_count = sum(1 for h in hotspots if h["acq_date"] == str(today))
    
    return {
        "today_count": today_count,
        "hotspots": hotspots
    }

@router.get("/logs")
async def get_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(CheckLog).order_by(desc(CheckLog.checked_at)).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [{
        "checked_at": l.checked_at.isoformat() if l.checked_at else datetime.now().isoformat(),
        "status": l.status,
        "hotspots_found": l.hotspots_found
    } for l in logs]

@router.post("/test-line")
async def test_line():
    line = LINEService()
    settings = get_settings()
    target = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
    
    if not target:
        return {"status": "error", "message": "LINE_GROUP_ID not configured"}
    
    now = datetime.now(THAI_TZ)
    
    # Simulated/Mock data to show how it looks in reality
    message_text = f"""🔔 [ทดสอบระบบ] แจ้งเตือนจุดความร้อน
📅 {now.strftime('%d/%m/%Y %H:%M')}
━━━━━━━━━━━━━━━━
🛰️ SNPP - 2 จุด (ถ่าย 01:25)
🛰️ NOAA20 - 1 จุด (ถ่าย 02:11)
━━━━━━━━━━━━━━━━
📍 รวมจำลอง: 3 จุด (2/3 ดาวเทียม)
🏔️ พื้นที่: กาญจนบุรี (Simulation)"""
    
    from linebot.v3.messaging import TextMessage
    message = TextMessage(text=message_text)
    
    try:
        await line.push_message(target, [message])
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Test LINE failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/check-now")
async def trigger_check(db: AsyncSession = Depends(get_db)):
    firms = FIRMSService()
    line = LINEService()
    notif_service = NotificationService(firms, line, db)
    
    # manual_trigger=True ensures it sends a LINE alert immediately
    result = await notif_service.check_and_notify(manual_trigger=True)
    
    # Add total count in DB for debugging
    from sqlalchemy import func
    stmt = select(func.count()).select_from(Hotspot)
    count_res = await db.execute(stmt)
    result["total_in_db"] = count_res.scalar()
    
    return result

@router.post("/settings")
async def update_setting(update: SettingUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Setting).where(Setting.key == update.key)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    
    if not setting:
        setting = Setting(key=update.key, value=update.value)
        db.add(setting)
    else:
        setting.value = update.value
    
    await db.commit()
    return {"status": "success", "key": update.key}
