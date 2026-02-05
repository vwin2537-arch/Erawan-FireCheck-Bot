import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from ..models import Hotspot, Notification, CheckLog, Setting
from .firms_service import FIRMSService
from .line_service import LINEService
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class NotificationService:
    def __init__(
        self,
        firms_service: FIRMSService,
        line_service: LINEService,
        db_session: AsyncSession
    ):
        self.firms = firms_service
        self.line = line_service
        self.db = db_session
        
    async def check_and_notify(self) -> Dict[str, Any]:
        """
        Main check routine: fetch, filter, save, and notify
        """
        start_time = datetime.now()
        logger.info(f"Starting check-and-notify routine at {start_time}")
        
        try:
            # 1. Fetch from FIRMS
            hotspots_data = await self.firms.get_all_sources()
            total_found = len(hotspots_data)
            
            # 1.5. No longer filtering by 'today' here to ensure we catch all 24h data
            # The API call already limits to 24h (day_range=1)
            # We want to save and potentially notify all hotspots returned
            today_hotspots = hotspots_data
            
            logger.info(f"Processing {len(today_hotspots)} hotspots from API")
            hotspots_data = today_hotspots
            
            # 2. Filter new hotspots (checking against DB)
            new_hotspots_data = await self.filter_new_hotspots(hotspots_data)
            new_count = len(new_hotspots_data)
            
            # 3. Save new hotspots
            hotspot_objs = []
            for h in new_hotspots_data:
                # Basic reverse geocoding simulation (real implementation would use geo_utils)
                # For now, we leave fields empty or use placeholders
                h["province"] = "กาญจนบุรี" 
                h["district"] = "-"
                
                obj = Hotspot(**h)
                self.db.add(obj)
                hotspot_objs.append(obj)
            
            await self.db.flush() # Get IDs
            
            # 4. If new hotspots found, notify
            notification_sent = False
            batch_id = str(uuid.uuid4())
            
            if new_count > 0:
                # Build satellites_found for the alert
                satellites_for_alert = {}
                for h in new_hotspots_data:
                    sat = h.get("satellite", "UNKNOWN")
                    if sat not in satellites_for_alert:
                        satellites_for_alert[sat] = {"count": 0, "time": ""}
                    satellites_for_alert[sat]["count"] += 1
                    # Use latest time for this satellite
                    if hasattr(h.get("acq_time"), 'strftime'):
                        satellites_for_alert[sat]["time"] = h["acq_time"].strftime("%H:%M")
                    else:
                        satellites_for_alert[sat]["time"] = str(h.get("acq_time", ""))[:5]
                
                # Fetch target group ID from settings or env
                target_to = settings.LINE_GROUP_ID.strip() if settings.LINE_GROUP_ID else None
                if not target_to:
                    # Try to get from DB settings
                    res = await self.db.execute(select(Setting).where(Setting.key == 'line_group_id'))
                    setting = res.scalar_one_or_none()
                    if setting:
                        target_to = setting.value
                
                if target_to:
                    try:
                        # NOTE: Message sending is now handled by scheduler_service._send_cumulative_update()
                        # to avoid duplicate messages. We just log the notification here.
                        notification_sent = True
                        
                        # Log notification
                        notif_log = Notification(
                            batch_id=batch_id,
                            hotspot_count=new_count,
                            message_text=f"Hotspot Alert: {new_count} points",
                            status="sent"
                        )
                        self.db.add(notif_log)
                        
                        # Mark hotspots as notified
                        for obj in hotspot_objs:
                            obj.notified = True
                            obj.notified_at = datetime.now()
                            
                    except Exception as e:
                        logger.error(f"Failed to send LINE notification: {e}")
            
            # 5. Log the check
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            check_log = CheckLog(
                hotspots_found=total_found,
                new_hotspots=new_count,
                api_response_time_ms=duration,
                status="success"
            )
            self.db.add(check_log)
            
            await self.db.commit()
            
            # Build satellites_found summary for scheduler
            satellites_found = {}
            for h in new_hotspots_data:
                sat = h.get("satellite", "UNKNOWN")
                if sat not in satellites_found:
                    satellites_found[sat] = {"count": 0, "time": ""}
                satellites_found[sat]["count"] += 1
                # Use latest time for this satellite
                if isinstance(h.get("acq_time"), datetime):
                    satellites_found[sat]["time"] = h["acq_time"].strftime("%H:%M")
                elif hasattr(h.get("acq_time"), 'strftime'):
                    satellites_found[sat]["time"] = h["acq_time"].strftime("%H:%M")
                else:
                    satellites_found[sat]["time"] = str(h.get("acq_time", ""))[:5]
            
            return {
                "checked_at": start_time,
                "hotspots_found": total_found,
                "new_hotspots": new_count,
                "notification_sent": notification_sent,
                "satellites_found": satellites_found
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error in check_and_notify: {e}")
            # Log error
            error_log = CheckLog(
                status="error",
                error_message=str(e)
            )
            self.db.add(error_log)
            await self.db.commit()
            raise

    async def filter_new_hotspots(self, hotspots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter hotspots that don't exist in the database yet
        """
        new_items = []
        for h in hotspots:
            # Check unique constraint: lat, lon, date, time, satellite
            stmt = select(Hotspot).where(
                and_(
                    Hotspot.latitude == h["latitude"],
                    Hotspot.longitude == h["longitude"],
                    Hotspot.acq_date == datetime.strptime(h["acq_date"], "%Y-%m-%d").date(),
                    Hotspot.acq_time == datetime.strptime(h["acq_time"], "%H%M").time(),
                    Hotspot.satellite == h["satellite"]
                )
            )
            result = await self.db.execute(stmt)
            if not result.scalar_one_or_none():
                # Convert date/time strings to objects for the model
                h_copy = h.copy()
                h_copy["acq_date"] = datetime.strptime(h["acq_date"], "%Y-%m-%d").date()
                h_copy["acq_time"] = datetime.strptime(h["acq_time"], "%H%M").time()
                new_items.append(h_copy)
        
        return new_items

    def create_summary(self, hotspots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a summary object for LINE Flex Message
        """
        if not hotspots:
            return {"total": 0}
            
        # Group by location (hardcoded simulation for now)
        # In a real app, this would use reverse geocoding
        locations = {}
        for h in hotspots:
            prov = h.get("province", "ไม่ทราบพื้นที่")
            dist = h.get("district", "N/A")
            
            if prov not in locations:
                locations[prov] = {}
            
            locations[prov][dist] = locations[prov].get(dist, 0) + 1
            
        # Get latest time and satellite from the batch
        latest_h = hotspots[0] # Just take the first one as a sample for the batch
        
        return {
            "total": len(hotspots),
            "satellite": latest_h["satellite"],
            "time": latest_h["acq_time"].strftime("%H:%M น."),
            "locations": locations
        }
