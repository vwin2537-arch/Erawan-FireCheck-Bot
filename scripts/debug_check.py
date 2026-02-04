import asyncio
import sys
import os
import logging

# Configure logging to see output in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.getcwd())

from app.database import AsyncSessionLocal
from app.services.firms_service import FIRMSService
from app.services.line_service import LINEService
from app.services.notification_service import NotificationService
from scripts.reset_data import reset_data

async def debug_check():
    # 1. Reset Data first
    await reset_data()
    
    print("\n--- Starting Debug Check ---")
    async with AsyncSessionLocal() as db:
        firms = FIRMSService()
        line = LINEService()
        service = NotificationService(firms, line, db)
        
        # Check settings
        from app.config import get_settings
        settings = get_settings()
        print(f"DEBUG: Loaded Settings LINE_GROUP_ID: '{settings.LINE_GROUP_ID}'")
        
        # Run check
        try:
            print("DEBUG: Calling service.check_and_notify()...")
            result = await service.check_and_notify()
            print(f"DEBUG: Result: {result}")
        except Exception as e:
            print(f"DEBUG: Exception during check: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_check())
