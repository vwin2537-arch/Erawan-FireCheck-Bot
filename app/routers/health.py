from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..database import get_db
import time

router = APIRouter(tags=["Support"])

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # Check DB
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
        
    return {
        "status": "healthy",
        "database": "ok" if db_ok else "error",
        "timestamp": time.time()
    }

@router.get("/status")
async def get_status():
    return {
        "app": "FIRMS LINE Bot",
        "version": "1.0.0",
        "current_time": time.ctime()
    }
