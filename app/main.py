"""
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.auth.router import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.decks import router as decks_router
from app.api.routes.csv import router as csv_router
from app.api.routes.study import router as study_router
from app.api.routes.statistics import router as statistics_router
from app.api.routes.frontend import router as frontend_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Chinese-English Flashcards",
    description="A web application for learning Chinese through flashcards",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(frontend_router)  # Frontend routes (no prefix)
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(decks_router, prefix="/api")
app.include_router(csv_router, prefix="/api")
app.include_router(study_router, prefix="/api")
app.include_router(statistics_router, prefix="/api")

# Templates
templates = Jinja2Templates(directory="app/templates")


# Remove the duplicate home route since it's now in frontend_router


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "environment": settings.environment}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )