from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..database import get_db
import time

router = APIRouter(tags=["Support"])

@router.get("/health")
async def health_check():
    # Simple health check - no DB dependency for faster startup
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@router.get("/status")
async def get_status():
    return {
        "app": "FIRMS LINE Bot",
        "version": "1.0.0",
        "current_time": time.ctime()
    }
