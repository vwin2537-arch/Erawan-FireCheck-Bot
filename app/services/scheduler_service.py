import logging
from datetime import datetime, timedelta
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
    
    # How long to keep checking after finding hotspots
    GRACE_PERIOD_HOURS = 1
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
        self.line_service = LINEService()
        # Track hotspots found during each peak period
        self.hotspots_found_this_period = 0
        # Track when first hotspot was found (for early sleep)
        self.first_hotspot_found_at = None
        # Track if we already went to early sleep
        self.early_sleep_sent = False
        
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
        
        # Smart Sleep: If we found hotspots and 1 hour has passed, go to sleep
        if self.first_hotspot_found_at:
            time_since_first = now - self.first_hotspot_found_at
            if time_since_first > timedelta(hours=self.GRACE_PERIOD_HOURS):
                # Already checked for 1 hour after finding hotspots, sleep now
                if not self.early_sleep_sent:
                    await self._send_early_sleep_message()
                    self.early_sleep_sent = True
                return

        interval = settings.CHECK_INTERVAL_PEAK
        
        # Run if it's the right minute according to the interval
        if now.minute % interval == 0:
            logger.info(f"Triggering peak-time check (Interval: {interval})")
            try:
                result = await self.notification_service.check_and_notify()
                # Track hotspots found during this period
                if result and result.get("new_hotspots", 0) > 0:
                    new_count = result["new_hotspots"]
                    self.hotspots_found_this_period += new_count
                    logger.info(f"Found {new_count} new hotspots!")
                    # Record first hotspot time for early sleep feature
                    if self.first_hotspot_found_at is None:
                        self.first_hotspot_found_at = now
                        logger.info(f"First hotspot found at {now}, will sleep after 1 hour")
            except Exception as e:
                logger.error(f"Error during scheduled check: {e}")

    async def _send_early_sleep_message(self):
        """Send message when going to early sleep after hotspot detection"""
        target = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
        if target:
            try:
                now = datetime.now(tz=ZoneInfo(settings.TIMEZONE))
                message = TextMessage(
                    text=f"😴 บอทเข้าสู่โหมดพักผ่อน\n📅 {now.strftime('%d/%m/%Y %H:%M')}\n✅ พบ {self.hotspots_found_this_period} จุดความร้อน\n💤 หลับจนถึงรอบถัดไป..."
                )
                await self.line_service.push_message(target, [message])
                logger.info("Sent early sleep message")
            except Exception as e:
                logger.error(f"Failed to send early sleep message: {e}")

    async def end_of_morning_peak(self):
        """Send heartbeat at end of morning peak if no hotspots found"""
        await self._send_heartbeat_if_needed("รอบดึก (01:30-06:00)")
        self._reset_period_state()
        
    async def end_of_afternoon_peak(self):
        """Send heartbeat at end of afternoon peak if no hotspots found"""
        await self._send_heartbeat_if_needed("รอบบ่าย (13:30-18:00)")
        self._reset_period_state()
    
    def _reset_period_state(self):
        """Reset all tracking variables for the next period"""
        self.hotspots_found_this_period = 0
        self.first_hotspot_found_at = None
        self.early_sleep_sent = False
    
    async def _send_heartbeat_if_needed(self, period_name: str):
        """Send a heartbeat message if no hotspots were found during the period"""
        # Skip heartbeat if we already sent early sleep message
        if self.early_sleep_sent:
            logger.info(f"Skipping heartbeat - already sent early sleep message")
            return
            
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
