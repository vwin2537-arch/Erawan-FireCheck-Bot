import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .notification_service import NotificationService
from .line_service import LINEService
from ..config import get_settings
from linebot.v3.messaging import TextMessage

logger = logging.getLogger(__name__)
settings = get_settings()

class SchedulerService:
    PEAK_HOURS = [
        (1, 30, 6, 0),    # 01:30 - 06:00 (Night overpass)
        (13, 30, 18, 0),  # 13:30 - 18:00 (Day overpass)
    ]
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
        self.line_service = LINEService()
        # Track hotspots found during each peak period
        self.hotspots_found_this_period = 0
        
    def start(self):
        """Start the scheduler with adaptive intervals"""
        # Main check job (runs every minute during peak hours)
        self.scheduler.add_job(
            self.adaptive_check_trigger,
            'cron',
            minute='*',
            id='adaptive_check_trigger'
        )
        
        # End-of-peak heartbeat jobs
        self.scheduler.add_job(
            self.end_of_morning_peak,
            'cron',
            hour=6,
            minute=0,
            id='end_of_morning_peak'
        )
        self.scheduler.add_job(
            self.end_of_afternoon_peak,
            'cron',
            hour=18,
            minute=0,
            id='end_of_afternoon_peak'
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started with timezone {settings.TIMEZONE}")
        
    async def adaptive_check_trigger(self):
        """
        Called every minute. Decides whether to run the main check
        based on current peak/off-peak settings.
        """
        now = datetime.now(tz=ZoneInfo(settings.TIMEZONE))
        
        is_peak = self.is_peak_time(now)
        
        # User requested to ONLY check during peak hours to save resources
        if not is_peak:
            return

        interval = settings.CHECK_INTERVAL_PEAK
        
        # Run if it's the right minute according to the interval
        if now.minute % interval == 0:
            logger.info(f"Triggering peak-time check (Interval: {interval})")
            try:
                result = await self.notification_service.check_and_notify()
                # Track hotspots found during this period
                if result and result.get("new_hotspots", 0) > 0:
                    self.hotspots_found_this_period += result["new_hotspots"]
            except Exception as e:
                logger.error(f"Error during scheduled check: {e}")

    async def end_of_morning_peak(self):
        """Send heartbeat at end of morning peak if no hotspots found"""
        await self._send_heartbeat_if_needed("รอบดึก (01:30-06:00)")
        
    async def end_of_afternoon_peak(self):
        """Send heartbeat at end of afternoon peak if no hotspots found"""
        await self._send_heartbeat_if_needed("รอบบ่าย (13:30-18:00)")
    
    async def _send_heartbeat_if_needed(self, period_name: str):
        """Send a heartbeat message if no hotspots were found during the period"""
        if self.hotspots_found_this_period == 0:
            # No hotspots found - send confirmation message
            target = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
            if target:
                try:
                    now = datetime.now(tz=ZoneInfo(settings.TIMEZONE))
                    message = TextMessage(
                        text=f"✅ บอทตรวจสอบ {period_name} เรียบร้อย\n📅 {now.strftime('%d/%m/%Y')}\n🔍 ไม่พบจุดความร้อนในพื้นที่"
                    )
                    await self.line_service.push_message(target, [message])
                    logger.info(f"Sent heartbeat message for {period_name}")
                except Exception as e:
                    logger.error(f"Failed to send heartbeat: {e}")
        else:
            logger.info(f"Skipping heartbeat - found {self.hotspots_found_this_period} hotspots during {period_name}")
        
        # Reset counter for next period
        self.hotspots_found_this_period = 0

    def is_peak_time(self, dt: datetime) -> bool:
        """Check if target time falls within any peak windows"""
        current_time = dt.time()
        for start_h, start_m, end_h, end_m in self.PEAK_HOURS:
            start = datetime.strptime(f"{start_h}:{start_m}", "%H:%M").time()
            end = datetime.strptime(f"{end_h}:{end_m}", "%H:%M").time()
            if start <= current_time <= end:
                return True
        return False

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown.")
