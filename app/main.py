import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing application...")
    
    # 1. Database initialization
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # 2. Services setup
    firms = FIRMSService()
    line = LINEService()
    
    # Check if we are running on Vercel
    import os
    is_vercel = os.environ.get("VERCEL") == "1"
    
    if not is_vercel:
        # Use a one-off session for scheduler if needed, or pass factory
        # For simplicity, we create a temporary service instance in the scheduler
        # but in a real app we might use a background task with its own session.
        logger.info("Starting scheduler (Local Mode)...")
        async with AsyncSessionLocal() as session:
            notif_service = NotificationService(firms, line, session)
            app.state.scheduler = SchedulerService(notif_service)
            app.state.scheduler.start()
    else:
        logger.info("Running on Vercel (Scheduler Disabled) - Using Vercel Cron")
    
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

# Static and Templates
# mkdir -p static/ templates/
templates = Jinja2Templates(directory="templates")

# Routers
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(webhook.router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "app_name": settings.APP_NAME})
