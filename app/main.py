import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from .database import engine, Base, AsyncSessionLocal
from .routers import health, dashboard, webhook
from .services.notification_service import NotificationService
from .services.firms_service import FIRMSService
from .services.line_service import LINEService
from .services.scheduler_service import SchedulerService
from .config import get_settings

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

# Get base directory for templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing application...")
    
    # 1. Database initialization
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")
    
    # 2. Services setup
    firms = FIRMSService()
    line = LINEService()
    
    # 3. Start Scheduler (Railway runs 24/7 so this works!)
    logger.info("Starting scheduler...")
    async with AsyncSessionLocal() as session:
        notif_service = NotificationService(firms, line, session)
        app.state.scheduler = SchedulerService(notif_service)
        app.state.scheduler.start()
    
    logger.info("Application startup complete.")
    yield
    
    # Shutdown logic
    logger.info("Cleaning up application...")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    debug=settings.DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates with absolute path
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Routers
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(webhook.router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "app_name": settings.APP_NAME})
