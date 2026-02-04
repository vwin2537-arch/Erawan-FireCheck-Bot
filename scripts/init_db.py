import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models import Setting
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

async def init_db():
    print("Creating tables...")
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Optional: drop existing
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

    print("Inserting default settings...")
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        default_settings = [
            Setting(key='monitoring_area', value='{"west": 97.5, "south": 5.5, "east": 105.6, "north": 20.5}'),
            Setting(key='check_interval_peak', value='10'),
            Setting(key='check_interval_offpeak', value='30'),
            Setting(key='min_confidence', value='nominal'),
            Setting(key='line_group_id', value=''),
            Setting(key='is_active', value='true')
        ]
        
        for setting in default_settings:
            # check if exists
            result = await session.execute(sa.select(Setting).where(Setting.key == setting.key))
            if not result.scalar_one_or_none():
                session.add(setting)
        
        await session.commit()
    print("Default settings inserted.")

if __name__ == "__main__":
    asyncio.run(init_db())
