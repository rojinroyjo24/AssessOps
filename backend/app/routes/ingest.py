"""
Ingestion API routes - handles batch ingestion of assessment attempt events.

This module implements the /api/ingest/attempts endpoint which:
1. Validates incoming event payloads
2. Creates/finds student and test records
3. Applies deduplication logic
4. Scores non-duplicate attempts
5. Returns an ingestion summary with counts
"""

import uuid
import time
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.student import Student
from app.models.test import Test
from app.models.attempt import Attempt
from app.services.deduplication import (
    normalize_email, normalize_phone, get_student_identity,
    check_duplicate
)
from app.services.scoring import compute_score
from app.logging_config import get_logger, log_with_context

router = APIRouter()
logger = get_logger("http")
db_logger = get_logger("db")


# ── Pydantic schemas ─────────────────────────────────────────

class AttemptEvent(BaseModel):
    """Schema for a single attempt event in the batch ingestion payload."""
    event_id: str = Field(..., description="Unique event identifier from source system")
    student_name: str = Field(..., description="Student's full name")
    student_email: Optional[str] = Field(None, description="Student email (may be null)")
    student_phone: Optional[str] = Field(None, description="Student phone number")
    test_id: str = Field(..., description="Test identifier from source system")
    test_name: str = Field(..., description="Test name/title")
    started_at: str = Field(..., description="ISO 8601 timestamp when test started")
    submitted_at: Optional[str] = Field(None, description="ISO 8601 timestamp when submitted")
    answers: dict = Field(default_factory=dict, description="Answers map: question_no -> A/B/C/D/SKIP")


class IngestionRequest(BaseModel):
    """Schema for batch ingestion request body."""
    events: List[AttemptEvent]


class IngestionSummary(BaseModel):
    """Schema for ingestion response with processing stats."""
    total_received: int
    ingested: int
    duplicates_detected: int
    scored: int
    errors: int
    details: list


def _parse_json(value):
    """Parse JSON from string or return dict as-is."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """
    Flexibly parse ISO 8601 timestamps from various formats.
    Returns timezone-naive UTC datetime for SQLite compatibility.
    Returns None if parsing fails.
    """
    if not ts_str:
        return None
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts_str)
        # Convert to naive UTC datetime for SQLite compatibility
        # This avoids "can't subtract offset-naive and offset-aware" errors
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError) as e:
        log_with_context(logger, "WARNING", "Failed to parse timestamp: {}".format(ts_str),
                        extra_data={"error": str(e)})
        return None


def find_or_create_student(db: Session, name: str, email: str, phone: str) -> Student:
    """Find an existing student by normalized identity or create a new one."""
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)
    
    student = None
    
    # Try to find by normalized email first
    if normalized_email:
        students_with_email = db.query(Student).filter(Student.email.isnot(None)).all()
        for s in students_with_email:
            if normalize_email(s.email) == normalized_email:
                student = s
                break
    
    # Fallback: try to find by normalized phone
    if not student and normalized_phone:
        students_with_phone = db.query(Student).filter(Student.phone.isnot(None)).all()
        for s in students_with_phone:
            if normalize_phone(s.phone) == normalized_phone:
                student = s
                break
    
    if student:
        log_with_context(db_logger, "DEBUG", "Found existing student: {}".format(student.full_name),
                        context={"student_id": str(student.id)})
        return student
    
    # Create new student
    student = Student(
        id=str(uuid.uuid4()),
        full_name=name,
        email=normalized_email,
        phone=normalized_phone,
        created_at=datetime.now(timezone.utc)
    )
    db.add(student)
    db.flush()
    
    log_with_context(db_logger, "INFO", "Created new student: {}".format(name),
                    context={"student_id": str(student.id)},
                    extra_data={"email": normalized_email, "phone": normalized_phone})
    return student


def find_or_create_test(db: Session, test_id_source: str, test_name: str) -> Test:
    """Find an existing test by name or create a new one."""
    test = db.query(Test).filter(Test.name == test_name).first()
    
    if test:
        return test
    
    # Create new test with default marking scheme
    test = Test(
        id=str(uuid.uuid4()),
        name=test_name,
        max_marks=400,
        negative_marking=json.dumps({"correct": 4, "wrong": -1, "skip": 0}),
        created_at=datetime.now(timezone.utc)
    )
    db.add(test)
    db.flush()
    
    log_with_context(db_logger, "INFO", "Created new test: {}".format(test_name),
                    context={"test_id": str(test.id)})
    return test


@router.post("/api/ingest/attempts", response_model=IngestionSummary)
def ingest_attempts(request: IngestionRequest, db: Session = Depends(get_db)):
    """
    Batch ingest assessment attempt events.
    
    Processing pipeline for each event:
    1. Parse and validate the event data
    2. Find or create student record (with identity normalization)
    3. Find or create test record
    4. Store raw payload in attempts table
    5. Apply deduplication logic against existing attempts
    6. Score non-duplicate attempts
    7. Mark duplicates with DEDUPED status
    """
    start_time = time.time()
    
    total = len(request.events)
    ingested = 0
    duplicates = 0
    scored = 0
    errors = 0
    details = []
    
    log_with_context(logger, "INFO", "Starting batch ingestion of {} events".format(total))
    
    for event in request.events:
        try:
            # Step 1: Parse timestamps
            started_at = parse_timestamp(event.started_at)
            submitted_at = parse_timestamp(event.submitted_at) if event.submitted_at else None
            
            if not started_at:
                errors += 1
                details.append({
                    "event_id": event.event_id,
                    "status": "ERROR",
                    "reason": "Could not parse started_at timestamp"
                })
                continue
            
            # Step 2: Find or create the student
            student = find_or_create_student(
                db, event.student_name, event.student_email, event.student_phone
            )
            
            # Step 3: Find or create the test
            test = find_or_create_test(db, event.test_id, event.test_name)
            
            # Step 4: Check for duplicate
            existing_attempts = db.query(Attempt).options(
                joinedload(Attempt.student)
            ).filter(
                Attempt.test_id == test.id,
                Attempt.status.in_(["INGESTED", "SCORED"])
            ).all()
            
            dedup_result = check_duplicate(
                {
                    "email": event.student_email,
                    "phone": event.student_phone,
                    "answers": event.answers,
                    "started_at": started_at
                },
                existing_attempts,
                test.id
            )
            
            # Step 5: Create the attempt record
            attempt = Attempt(
                id=str(uuid.uuid4()),
                student_id=student.id,
                test_id=test.id,
                source_event_id=event.event_id,
                started_at=started_at,
                submitted_at=submitted_at,
                answers=json.dumps(event.answers),
                raw_payload=json.dumps(event.dict()),
                status="DEDUPED" if dedup_result["is_duplicate"] else "INGESTED",
                duplicate_of_attempt_id=str(dedup_result["canonical_attempt_id"]) if dedup_result.get("canonical_attempt_id") else None
            )
            db.add(attempt)
            db.flush()
            
            if dedup_result["is_duplicate"]:
                duplicates += 1
                details.append({
                    "event_id": event.event_id,
                    "attempt_id": str(attempt.id),
                    "status": "DEDUPED",
                    "canonical_attempt_id": str(dedup_result["canonical_attempt_id"])
                })
            else:
                score = compute_score(attempt, test, db)
                scored += 1
                details.append({
                    "event_id": event.event_id,
                    "attempt_id": str(attempt.id),
                    "status": "SCORED",
                    "score": float(score.score)
                })
            
            ingested += 1
            
        except Exception as e:
            errors += 1
            details.append({
                "event_id": event.event_id,
                "status": "ERROR",
                "reason": str(e)
            })
            log_with_context(logger, "ERROR", "Failed to process event {}: {}".format(event.event_id, str(e)),
                           context={"event_id": event.event_id})
            db.rollback()
    
    # Commit all successful operations
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        log_with_context(logger, "ERROR", "Failed to commit batch: {}".format(str(e)))
        raise HTTPException(status_code=500, detail="Database commit failed")
    
    duration_ms = (time.time() - start_time) * 1000
    
    log_with_context(logger, "INFO",
        "Ingestion complete: {} ingested, {} duplicates, {} scored, {} errors".format(
            ingested, duplicates, scored, errors),
        extra_data={"duration_ms": round(duration_ms, 2), "total_events": total})
    
    return IngestionSummary(
        total_received=total,
        ingested=ingested,
        duplicates_detected=duplicates,
        scored=scored,
        errors=errors,
        details=details
    )
