from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
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
    # Use Thai timezone to get today's and yesterday's date
    thai_now = datetime.now(THAI_TZ)
    today = thai_now.date()
    yesterday = today - timedelta(days=1)
    
    # Get hotspots from today AND yesterday to handle day transition
    from sqlalchemy import or_
    stmt = select(Hotspot).where(
        or_(Hotspot.acq_date == today, Hotspot.acq_date == yesterday)
    ).order_by(desc(Hotspot.acq_date), desc(Hotspot.acq_time))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/notifications")
async def get_notifications(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(Notification).order_by(desc(Notification.sent_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/logs")
async def get_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(CheckLog).order_by(desc(CheckLog.checked_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/check-now")
async def trigger_check(db: AsyncSession = Depends(get_db)):
    firms = FIRMSService()
    line = LINEService()
    notif_service = NotificationService(firms, line, db)
    
    result = await notif_service.check_and_notify()
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
