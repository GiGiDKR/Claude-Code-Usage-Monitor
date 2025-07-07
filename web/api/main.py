"""
Main FastAPI application for Claude Code Usage Monitor.

This module contains the main FastAPI application instance and configuration.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .exceptions import register_exception_handlers
from .middleware.logging import LoggingMiddleware
from .middleware.security import RateLimitMiddleware, SecurityMiddleware
from .routers import config, status, usage
from .websocket.manager import websocket_router


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Claude Code Usage Monitor API",
        description="Real-time monitoring API for Claude AI token usage",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware
    app.add_middleware(SecurityMiddleware)

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware, calls_per_minute=100)

    # Custom logging middleware
    app.add_middleware(LoggingMiddleware)

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(status.router, prefix="/api/v1", tags=["status"])
    app.include_router(usage.router, prefix="/api/v1", tags=["usage"])
    app.include_router(config.router, prefix="/api/v1", tags=["config"])

    # Include WebSocket router
    app.include_router(websocket_router)

    # Static files for frontend (will be added later)
    static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
