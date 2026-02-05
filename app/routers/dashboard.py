from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from typing import List
from ..database import get_db
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
        time_str = h.acq_time
        if time_str and ":" not in time_str and len(time_str) == 4:
            time_str = f"{time_str[:2]}:{time_str[2:]}"
        
        hotspots.append({
            "id": h.id,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "acq_date": str(h.acq_date),
            "acq_time": time_str,
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
    # Add Z to end of checked_at to help JS understand it's UTC
    return [{
        "checked_at": l.checked_at.isoformat() + "Z",
        "status": l.status,
        "hotspots_found": l.hotspots_found
    } for l in logs]

@router.post("/test-line")
async def test_line():
    from .dashboard import THAI_TZ
    line = LINEService()
    settings = get_settings()
    target = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
    
    if not target:
        return {"status": "error", "message": "LINE_GROUP_ID not configured"}
    
    now = datetime.now(THAI_TZ)
    from linebot.v3.messaging import TextMessage
    message = TextMessage(text=f"🔔 ทดสอบการทำงานของบอท\n📅 เวลา: {now.strftime('%H:%M:%S')}\n✅ บอทเชื่อมต่อกับระบบ Dashboard เรียบร้อยแล้ว")
    
    try:
        await line.push_message(target, [message])
        return {"status": "success"}
    except Exception as e:
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
