import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .notification_service import NotificationService
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class SchedulerService:
    # Peak hours for Thailand (local time) based on satellite overpass
    PEAK_HOURS = [
        (2, 30, 6, 0),    # 02:30 - 06:00 (Night overpass + delay)
        (14, 30, 18, 0),  # 14:30 - 18:00 (Day overpass + delay)
    ]
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
        
    def start(self):
        """Start the scheduler with adaptive intervals"""
        # Add a management job that runs every minute to decide whether to trigger the check
        self.scheduler.add_job(
            self.adaptive_check_trigger,
            'cron',
            minute='*',
            id='adaptive_check_trigger'
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
        interval = settings.CHECK_INTERVAL_PEAK if is_peak else settings.CHECK_INTERVAL_OFFPEAK
        
        # Run if it's the right minute according to the interval
        if now.minute % interval == 0:
            logger.info(f"Triggering adaptive check (Is Peak: {is_peak}, Interval: {interval})")
            try:
                # Note: This requires a DB session. We'll need a better way to handle session
                # lifecycle in the implementation of main.py or by passing a session factory.
                # For now, we assume the notification_service can handle its own session
                # or we use a separate approach in main.py.
                await self.notification_service.check_and_notify()
            except Exception as e:
                logger.error(f"Error during scheduled check: {e}")

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
