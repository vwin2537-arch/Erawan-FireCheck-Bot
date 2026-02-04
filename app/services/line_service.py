import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer
)
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class LINEService:
    """
    LINE Messaging API Integration
    Documentation: https://developers.line.biz/en/docs/messaging-api/
    """
    
    def __init__(self):
        self.configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN.strip())
        
    async def push_message(self, to: str, messages: List[Any]):
        """
        Send push message to a user or group (Async wrapper for Sync SDK)
        """
        def _push():
            with ApiClient(self.configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                try:
                    push_message_request = PushMessageRequest(
                        to=to,
                        messages=messages
                    )
                    line_bot_api.push_message(push_message_request)
                    logger.info(f"Successfully sent LINE push message to {to}")
                except Exception as e:
                    logger.error(f"Error sending LINE push message: {e}")
                    raise e

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _push)

    async def send_hotspot_alert(
        self,
        to: str,
        summary: Dict[str, Any]
    ):
        """
        Send a formatted hotspot alert via Flex Message
        """
        flex_contents = self.create_hotspot_flex_message(summary)
        flex_message = FlexMessage(
            alt_text=f"🔥 แจ้งเตือนจุดความร้อน {summary['total']} จุด",
            contents=FlexContainer.from_json(json.dumps(flex_contents))
        )
        
        await self.push_message(to, [flex_message])

    async def send_satellite_alert(
        self,
        to: str,
        satellites_data: Dict[str, Dict[str, Any]],
        all_satellites: List[str] = None
    ):
        """
        Send a text-based alert with satellite breakdown
        satellites_data format: {"VIIRS_SNPP": {"count": 3, "time": "12:45"}, ...}
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        if all_satellites is None:
            all_satellites = ["VIIRS_SNPP", "VIIRS_NOAA20", "VIIRS_NOAA21"]
        
        now = datetime.now(tz=ZoneInfo(settings.TIMEZONE))
        
        # Build satellite summary lines
        sat_lines = []
        total = 0
        for sat in all_satellites:
            if sat in satellites_data:
                data = satellites_data[sat]
                sat_name = sat.replace("VIIRS_", "")
                sat_lines.append(f"🛰️ {sat_name} - {data['count']} จุด (ถ่าย {data['time']})")
                total += data["count"]
        
        # Count how many satellites reported
        reported_count = len(satellites_data)
        
        message_text = f"""🔥 แจ้งเตือนจุดความร้อน
📅 {now.strftime('%d/%m/%Y %H:%M')}
━━━━━━━━━━━━━━━━
{chr(10).join(sat_lines)}
━━━━━━━━━━━━━━━━
📍 รวม: {total} จุด ({reported_count}/{len(all_satellites)} ดาวเทียม)
🏔️ พื้นที่: กาญจนบุรี"""

        message = TextMessage(text=message_text)
        await self.push_message(to, [message])

    def create_hotspot_flex_message(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Flex Message JSON structure for hotspot alert
        """
        # Summary format:
        # {
        #   "total": int,
        #   "satellite": str,
        #   "time": str,
        #   "locations": {
        #     "เชียงใหม่": {"แม่แจ่ม": 3, "อมก๋อย": 2},
        #     "ลำปาง": {"แจ้ห่ม": 3}
        #   }
        # }
        
        # Build location rows
        location_contents = []
        for province, districts in summary.get("locations", {}).items():
            location_contents.append({
                "type": "text",
                "text": f"🏔️ {province} ({sum(districts.values())} จุด)",
                "weight": "bold",
                "size": "sm",
                "margin": "md"
            })
            for district, count in districts.items():
                location_contents.append({
                    "type": "text",
                    "text": f"• {district} - {count} จุด",
                    "size": "xs",
                    "color": "#666666",
                    "margin": "xs"
                })

        return {
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
                    {
                        "type": "text",
                        "text": f"📍 พบ {summary['total']} จุด ในพื้นที่รับผิดชอบ",
                        "weight": "bold",
                        "size": "md",
                        "color": "#333333"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    *location_contents,
                    {
                        "type": "separator",
                        "margin": "xl"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {"type": "text", "text": "🛰️ ดาวเทียม", "color": "#aaaaaa", "size": "sm", "flex": 2},
                                    {"type": "text", "text": summary.get("satellite", "N/A"), "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {"type": "text", "text": "🕐 เวลาถ่าย", "color": "#aaaaaa", "size": "sm", "flex": 2},
                                    {"type": "text", "text": summary.get("time", "N/A"), "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#FF5555",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ ดูแผนที่ (FIRMS)",
                            "uri": "https://firms.modaps.eosdis.nasa.gov/map/"
                        }
                    }
                ],
                "flex": 0
            }
        }
