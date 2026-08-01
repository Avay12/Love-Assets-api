import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.api.router import main_router
from app.utils.storage import ensure_upload_dir_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    ensure_upload_dir_exists()
    await init_db()
    yield
    # Shutdown actions (if any)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware enabling all origins by default for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static uploads directory for serving uploaded photos & files
upload_dir = ensure_upload_dir_exists()
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# Include API endpoints
app.include_router(main_router)


@app.get("/", summary="Root Endpoint")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_STR}/health",
    }
