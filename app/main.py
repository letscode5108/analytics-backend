import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import auth, post, analytics

from utils.scheduler_service import scheduler
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global task to hold the scheduler
scheduler_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    global scheduler_task
    
    # Startup: Start the background scheduler
    logger.info(" Starting background scheduler...")
    scheduler_task = asyncio.create_task(
        scheduler.run_scheduler(interval_seconds=30)  # Check every 30 seconds
    )
    logger.info(" Background scheduler started")
    
    yield  # App is running
    
    # Shutdown: Stop the scheduler
    logger.info(" Stopping background scheduler...")
    scheduler.stop_scheduler()
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("Background scheduler stopped")


# Simple settings
APP_NAME = "LinkedIn Analytics Backend API"
APP_VERSION = "1.0.0"

# Create FastAPI app instance
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="A LinkedIn Analytics Backend API built with FastAPI and PostgreSQL",
    docs_url="/docs",  # Swagger UI at /docs
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth.router, prefix="/api/v1")
app.include_router(post.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "linkedin-analytics-backend"}

# Run the app
if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # Changed from "app.main:app" to just "main:app"
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )