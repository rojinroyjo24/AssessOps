"""
Assessment Ops Mini Platform - FastAPI Application Entry Point.

This is the main application module that:
1. Initializes the FastAPI app with CORS middleware
2. Sets up structured JSON logging
3. Implements request ID middleware (X-Request-ID header)
4. Registers all API route handlers
5. Provides health check endpoint

The application follows a modular architecture:
- routes/: API endpoint handlers
- models/: SQLAlchemy ORM models
- services/: Business logic (deduplication, scoring)
- logging_config.py: Structured logging configuration
- database.py: Database connection management
"""

import time
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import (
    setup_logging, get_logger, log_with_context,
    request_id_var, generate_request_id
)
from app.routes import ingest, attempts, leaderboard
from app.database import DATABASE_URL, create_tables

# Import all models so they are registered with Base.metadata
from app.models.student import Student
from app.models.test import Test
from app.models.attempt import Attempt
from app.models.attempt_score import AttemptScore
from app.models.flag import Flag

# ──────────────────────────────────────────────────────────────
# Initialize structured logging BEFORE anything else
# ──────────────────────────────────────────────────────────────
setup_logging()
logger = get_logger("http")

# Auto-create tables for SQLite local development
if DATABASE_URL.startswith("sqlite"):
    logger.info("Using SQLite — creating tables directly")
    create_tables()

# ──────────────────────────────────────────────────────────────
# Create FastAPI application
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Assessment Ops Mini Platform",
    description=(
        "A platform for ingesting student assessment attempts from coaching centres, "
        "deduplicating noisy events, computing scores with negative marking, "
        "and providing analytics via REST APIs."
    ),
    version="1.0.0",
    docs_url="/docs",        # Swagger UI at /docs
    redoc_url="/redoc"       # ReDoc at /redoc
)

# ──────────────────────────────────────────────────────────────
# CORS Middleware
#
# Allows the React frontend (port 3000) to call the backend (port 8000).
# In production, restrict origins to the actual frontend domain.
# ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],                # Allow all HTTP methods
    allow_headers=["*"],                # Allow all headers
    expose_headers=["X-Request-ID"]     # Expose request ID header to frontend
)


# ──────────────────────────────────────────────────────────────
# Request ID Middleware
#
# Generates a unique UUID per incoming request and:
# 1. Stores it in a context variable (available to all log entries)
# 2. Returns it in the X-Request-ID response header
# 3. Logs request start/end with latency measurement
# ──────────────────────────────────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Middleware that generates a unique request ID for every HTTP request.
    
    This enables end-to-end request tracing across all log entries.
    The request ID is:
    - Generated as a UUID v4
    - Stored in a context variable (accessible from any log call)
    - Included in the X-Request-ID response header
    - Logged at request start and completion
    """
    # Generate and set request ID
    req_id = generate_request_id()
    request_id_var.set(req_id)
    
    # Record request start time for latency calculation
    start_time = time.time()
    
    # Log incoming request
    log_with_context(logger, "INFO",
        f"Request started: {request.method} {request.url.path}",
        context={"request_id": req_id},
        extra_data={
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "query_params": dict(request.query_params)
        })
    
    # Process the request
    response = await call_next(request)
    
    # Calculate request duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = req_id
    
    # Log request completion with latency
    log_with_context(logger, "INFO",
        f"Request completed: {request.method} {request.url.path} → {response.status_code}",
        context={"request_id": req_id},
        extra_data={
            "duration_ms": round(duration_ms, 2),
            "status_code": response.status_code
        })
    
    return response


# ──────────────────────────────────────────────────────────────
# Register API routes
# ──────────────────────────────────────────────────────────────
app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(attempts.router, tags=["Attempts"])
app.include_router(leaderboard.router, tags=["Leaderboard"])


# ──────────────────────────────────────────────────────────────
# Health check endpoint
# ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint for Docker health checks and monitoring.
    
    Returns a simple status response to verify the application is running.
    """
    return {"status": "healthy", "service": "assessment-ops-backend", "version": "1.0.0"}


@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information."""
    return {
        "service": "Assessment Ops Mini Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "ingest": "POST /api/ingest/attempts",
            "attempts_list": "GET /api/attempts",
            "attempt_detail": "GET /api/attempts/{id}",
            "recompute": "POST /api/attempts/{id}/recompute",
            "flag": "POST /api/attempts/{id}/flag",
            "leaderboard": "GET /api/leaderboard"
        }
    }
