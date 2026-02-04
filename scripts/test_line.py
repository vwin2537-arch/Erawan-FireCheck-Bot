import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.line_service import LINEService
from app.config import get_settings

async def test_line():
    print("Testing LINE Messaging...")
    settings = get_settings()
    
    print(f"Group ID: {settings.LINE_GROUP_ID}")
    print(f"Token (first 10 chars): {settings.LINE_CHANNEL_ACCESS_TOKEN[:10]}...")
    
    line = LINEService()
    
    # Mock summary data
    summary = {
        "total": 99,
        "satellite": "TEST_SAT",
        "time": "12:00 น.",
        "locations": {
            "ทดสอบ": {"เมือง": 1}
        }
    }
    
    try:
        print("Sending test message...")
        await line.send_hotspot_alert(settings.LINE_GROUP_ID, summary)
        print("✅ Message sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_line())
