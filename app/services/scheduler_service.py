import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .notification_service import NotificationService
from .line_service import LINEService
from .firms_service import FIRMSService
from ..config import get_settings
from linebot.v3.messaging import TextMessage

logger = logging.getLogger(__name__)
settings = get_settings()

class SchedulerService:
    PEAK_HOURS = [
        (1, 30, 6, 0),    # 01:30 - 06:00 (Night overpass)
        (13, 30, 18, 0),  # 13:30 - 18:00 (Day overpass)
    ]
    
    # All satellites we track
    ALL_SATELLITES = ["VIIRS_SNPP", "VIIRS_NOAA20", "VIIRS_NOAA21"]
    
    # How long to keep checking after ALL satellites have reported
    GRACE_PERIOD_HOURS = 1
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
        self.line_service = LINEService()
        
        # Track cumulative satellite data for the period
        # Format: {"VIIRS_SNPP": {"count": 3, "time": "02:15"}, ...}
        self.satellite_data = {}
        
        # Track when all satellites have reported (for sleep timer)
        self.all_satellites_reported_at = None
        
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
        
        # Smart Sleep: If ALL satellites reported and 1 hour has passed, go to sleep
        if self.all_satellites_reported_at:
            time_since_complete = now - self.all_satellites_reported_at
            if time_since_complete > timedelta(hours=self.GRACE_PERIOD_HOURS):
                # All satellites reported and 1 hour passed, sleep now
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
                
                # Track new hotspots by satellite
                if result and result.get("new_hotspots", 0) > 0:
                    new_satellites = result.get("satellites_found", {})
                    has_new_data = False
                    
                    for sat, data in new_satellites.items():
                        if data["count"] > 0:
                            # Update cumulative satellite data
                            if sat not in self.satellite_data:
                                self.satellite_data[sat] = {"count": 0, "time": data["time"]}
                            self.satellite_data[sat]["count"] += data["count"]
                            self.satellite_data[sat]["time"] = data["time"]
                            has_new_data = True
                    
                    if has_new_data:
                        # Send cumulative message
                        await self._send_cumulative_update()
                        
                        # Check if all satellites have reported
                        reported_sats = set(self.satellite_data.keys())
                        all_sats = set(self.ALL_SATELLITES)
                        if reported_sats >= all_sats and self.all_satellites_reported_at is None:
                            self.all_satellites_reported_at = now
                            logger.info(f"All 3 satellites reported! Will sleep in 1 hour.")
                            
            except Exception as e:
                logger.error(f"Error during scheduled check: {e}")

    async def _send_cumulative_update(self):
        """Send cumulative update message with all satellites found so far"""
        target = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
        if not target:
            return
            
        try:
            now = datetime.now(tz=ZoneInfo(settings.TIMEZONE))
            
            # Build satellite summary lines
            sat_lines = []
            total = 0
            for sat in self.ALL_SATELLITES:
                if sat in self.satellite_data:
                    data = self.satellite_data[sat]
                    sat_name = sat.replace("VIIRS_", "")
                    sat_lines.append(f"🛰️ {sat_name} - {data['count']} จุด (ถ่าย {data['time']})")
                    total += data["count"]
            
            # Count how many satellites reported
            reported_count = len(self.satellite_data)
            
            message_text = f"""🔥 แจ้งเตือนจุดความร้อน
📅 {now.strftime('%d/%m/%Y %H:%M')}
━━━━━━━━━━━━━━━━
{chr(10).join(sat_lines)}
━━━━━━━━━━━━━━━━
📍 รวม: {total} จุด ({reported_count}/3 ดาวเทียม)
🏔️ พื้นที่: กาญจนบุรี"""

            message = TextMessage(text=message_text)
            await self.line_service.push_message(target, [message])
            logger.info(f"Sent cumulative update: {total} hotspots from {reported_count} satellites")
            
        except Exception as e:
            logger.error(f"Failed to send cumulative update: {e}")

    async def _send_early_sleep_message(self):
        """Send message when going to early sleep after all satellites reported"""
        target = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
        if target:
            try:
                now = datetime.now(tz=ZoneInfo(settings.TIMEZONE))
                total = sum(d["count"] for d in self.satellite_data.values())
                message = TextMessage(
                    text=f"😴 บอทเข้าสู่โหมดพักผ่อน\n📅 {now.strftime('%d/%m/%Y %H:%M')}\n✅ ครบ 3 ดาวเทียม พบ {total} จุดความร้อน\n💤 หลับจนถึงรอบถัดไป..."
                )
                await self.line_service.push_message(target, [message])
                logger.info("Sent early sleep message (all satellites done)")
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
        self.satellite_data = {}
        self.all_satellites_reported_at = None
        self.early_sleep_sent = False
    
    async def _send_heartbeat_if_needed(self, period_name: str):
        """Send a heartbeat message if no hotspots were found during the period"""
        # Skip heartbeat if we already sent early sleep message
        if self.early_sleep_sent:
            logger.info(f"Skipping heartbeat - already sent early sleep message")
            return
            
        if not self.satellite_data:
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
            total = sum(d["count"] for d in self.satellite_data.values())
            logger.info(f"Skipping heartbeat - found {total} hotspots during {period_name}")

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
