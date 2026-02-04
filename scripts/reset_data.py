import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def reset_data():
    print("Clearing data...")
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM hotspots"))
        await session.execute(text("DELETE FROM notifications"))
        await session.execute(text("DELETE FROM check_logs"))
        await session.commit()
    print("Data cleared. You can now Trigger Check to test notifications.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_data())
