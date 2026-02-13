"""
Database connection and session management module.

Uses SQLAlchemy for ORM operations. Supports PostgreSQL (production/Docker)
and SQLite (local development fallback).
Provides session factory and dependency injection for FastAPI routes.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Read database URL from environment
# Fallback to SQLite for local development when PostgreSQL is not available
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./assessment_ops.db"
)

# Configure engine kwargs based on database type
# SQLite does not support pool_size, max_overflow, or pool_pre_ping
engine_kwargs = {"echo": False}

if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })
elif DATABASE_URL.startswith("sqlite"):
    # SQLite needs check_same_thread=False for FastAPI (multi-threaded)
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Enable WAL mode and foreign keys for SQLite (better concurrency)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory - creates new database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """
    FastAPI dependency that provides a database session.
    
    Yields a session and ensures proper cleanup after request completion.
    This pattern guarantees connections are returned to the pool even if
    an exception occurs during request processing.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables directly (used for SQLite local dev).
    For PostgreSQL, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
