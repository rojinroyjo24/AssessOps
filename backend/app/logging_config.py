"""
Structured JSON logging configuration (Monolog-style).

Provides structured logging with channels (http, db, dedup, scoring),
request ID tracking, and context-rich log entries. All log output is
valid JSON written to stdout for container log aggregation.
"""

import logging
import json
import os
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar

# ──────────────────────────────────────────────────────────────
# Context variable to track request ID across async operations.
# Each incoming HTTP request gets a unique UUID, which is then
# attached to every log entry produced during that request.
# ──────────────────────────────────────────────────────────────
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class StructuredJsonFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs Monolog-style JSON log entries.
    
    Each log line is a single JSON object containing:
    - timestamp: ISO 8601 timestamp in UTC
    - level: Log severity (INFO, WARNING, ERROR, DEBUG)
    - message: Human-readable log message
    - channel: Log source category (http, db, dedup, scoring, app)
    - context: Business context (request_id, attempt_id, etc.)
    - extra: Additional metadata (ip, duration_ms, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        # Build the structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "channel": getattr(record, "channel", record.name.split(".")[-1] if "." in record.name else "app"),
            "context": {
                "request_id": request_id_var.get(""),
                **(getattr(record, "context", {}) or {})
            },
            "extra": getattr(record, "extra_data", {}) or {}
        }
        return json.dumps(log_entry, default=str)


def setup_logging():
    """
    Configure the root logger and all channel-specific loggers.
    
    Sets up:
    - Root logger with structured JSON formatter
    - Channel loggers: http, db, dedup, scoring
    - All output directed to stdout (container-friendly)
    """
    # Create the JSON formatter
    formatter = StructuredJsonFormatter()

    # Configure stdout handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root_logger.handlers = [handler]

    # Create channel-specific loggers
    # These loggers inherit the root handler but have distinct names
    # so log entries can be filtered by channel
    channels = ["http", "db", "dedup", "scoring"]
    for channel in channels:
        logger = logging.getLogger(f"app.{channel}")
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    return root_logger


def get_logger(channel: str) -> logging.Logger:
    """
    Get a channel-specific logger.
    
    Args:
        channel: Log channel name (http, db, dedup, scoring)
    
    Returns:
        Logger instance for the specified channel
    """
    return logging.getLogger(f"app.{channel}")


def log_with_context(logger: logging.Logger, level: str, message: str,
                     context: dict = None, extra_data: dict = None):
    """
    Emit a structured log entry with business context and extra metadata.
    
    This is the primary logging function used throughout the application.
    It attaches business context (attempt_id, student_id, etc.) and extra 
    metadata (duration_ms, ip, etc.) to each log entry.
    
    Args:
        logger: The channel logger to use
        level: Log level string (INFO, WARNING, ERROR, DEBUG)
        message: Human-readable log message
        context: Business context dict (attempt_id, student_id, test_id)
        extra_data: Additional metadata dict (ip, duration_ms, query_params)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    # Use the `extra` parameter to pass structured data to the formatter
    logger.log(
        log_level,
        message,
        extra={"context": context or {}, "extra_data": extra_data or {}, "channel": logger.name.split(".")[-1]}
    )


def generate_request_id() -> str:
    """Generate a new UUID for request tracking."""
    return str(uuid.uuid4())
