"""
Attempts API routes - CRUD operations and actions on assessment attempts.

Provides endpoints for:
- Listing attempts with filters and pagination
- Viewing attempt details
- Recomputing scores
- Flagging attempts for review
"""

import uuid
import time
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.attempt import Attempt
from app.models.attempt_score import AttemptScore
from app.models.student import Student
from app.models.test import Test
from app.models.flag import Flag
from app.services.scoring import compute_score
from app.logging_config import get_logger, log_with_context

router = APIRouter()
logger = get_logger("http")


# ── Pydantic schemas ─────────────────────────────────────────

class FlagRequest(BaseModel):
    """Schema for creating a flag on an attempt."""
    reason: str


class FlagResponse(BaseModel):
    """Schema for flag creation response."""
    id: str
    attempt_id: str
    reason: str
    created_at: str


def _parse_json(value):
    """Parse JSON from string or return as-is if already dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {} if value is None else value


def serialize_attempt(attempt: Attempt) -> dict:
    """Serialize an Attempt ORM object to a dict for API response."""
    # Count duplicates that reference this attempt as canonical
    duplicate_count = 0
    if attempt.student and attempt.student.attempts:
        duplicate_count = len([
            a for a in attempt.student.attempts
            if a.duplicate_of_attempt_id == attempt.id
        ])
    
    # Parse JSON fields
    answers = _parse_json(attempt.answers)
    raw_payload = _parse_json(attempt.raw_payload)
    negative_marking = _parse_json(attempt.test.negative_marking) if attempt.test else {}
    
    # Parse score explanation
    score_data = None
    if attempt.score:
        explanation = _parse_json(attempt.score.explanation)
        score_data = {
            "correct": attempt.score.correct,
            "wrong": attempt.score.wrong,
            "skipped": attempt.score.skipped,
            "accuracy": float(attempt.score.accuracy),
            "net_correct": attempt.score.net_correct,
            "score": float(attempt.score.score),
            "computed_at": attempt.score.computed_at.isoformat() if attempt.score.computed_at else None,
            "explanation": explanation
        }
    
    result = {
        "id": str(attempt.id),
        "student_id": str(attempt.student_id),
        "test_id": str(attempt.test_id),
        "source_event_id": attempt.source_event_id,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "answers": answers,
        "raw_payload": raw_payload,
        "status": attempt.status,
        "duplicate_of_attempt_id": str(attempt.duplicate_of_attempt_id) if attempt.duplicate_of_attempt_id else None,
        "student": {
            "id": str(attempt.student.id),
            "full_name": attempt.student.full_name,
            "email": attempt.student.email,
            "phone": attempt.student.phone
        } if attempt.student else None,
        "test": {
            "id": str(attempt.test.id),
            "name": attempt.test.name,
            "max_marks": attempt.test.max_marks,
            "negative_marking": negative_marking
        } if attempt.test else None,
        "score": score_data,
        "flags": [
            {
                "id": str(f.id),
                "reason": f.reason,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in (attempt.flags or [])
        ],
        "duplicate_count": duplicate_count
    }
    return result


@router.get("/api/attempts")
def list_attempts(
    test_id: Optional[str] = Query(None, description="Filter by test ID"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    has_duplicates: Optional[bool] = Query(None, description="Filter duplicates"),
    date_from: Optional[str] = Query(None, description="Filter by start date"),
    date_to: Optional[str] = Query(None, description="Filter by end date"),
    search: Optional[str] = Query(None, description="Search student name/email/phone"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """List attempts with filtering, search, and pagination."""
    start_time = time.time()
    
    query = db.query(Attempt).options(
        joinedload(Attempt.student),
        joinedload(Attempt.test),
        joinedload(Attempt.score),
        joinedload(Attempt.flags)
    )
    
    # Apply filters
    if test_id:
        query = query.filter(Attempt.test_id == test_id)
    if student_id:
        query = query.filter(Attempt.student_id == student_id)
    if status:
        query = query.filter(Attempt.status == status.upper())
    if has_duplicates is not None:
        if has_duplicates:
            query = query.filter(Attempt.duplicate_of_attempt_id.isnot(None))
        else:
            query = query.filter(Attempt.duplicate_of_attempt_id.is_(None))
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(Attempt.started_at >= from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(Attempt.started_at <= to_date)
        except ValueError:
            pass
    if search:
        query = query.join(Student).filter(
            (Student.full_name.ilike("%{}%".format(search))) |
            (Student.email.ilike("%{}%".format(search))) |
            (Student.phone.ilike("%{}%".format(search)))
        )
    
    # Get total count
    total_count = query.count()
    
    # Paginate
    offset = (page - 1) * per_page
    attempts = query.order_by(Attempt.started_at.desc()).offset(offset).limit(per_page).all()
    
    duration_ms = (time.time() - start_time) * 1000
    log_with_context(logger, "INFO",
        "Listed {} attempts (page {}, total {})".format(len(attempts), page, total_count),
        extra_data={"duration_ms": round(duration_ms, 2)})
    
    return {
        "data": [serialize_attempt(a) for a in attempts],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "total_pages": (total_count + per_page - 1) // per_page
        }
    }


@router.get("/api/attempts/{attempt_id}")
def get_attempt(attempt_id: str, db: Session = Depends(get_db)):
    """Get detailed information for a specific attempt."""
    attempt = db.query(Attempt).options(
        joinedload(Attempt.student).joinedload(Student.attempts),
        joinedload(Attempt.test),
        joinedload(Attempt.score),
        joinedload(Attempt.flags)
    ).filter(Attempt.id == attempt_id).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    result = serialize_attempt(attempt)
    
    # Build duplicate thread
    duplicate_thread = []
    if attempt.duplicate_of_attempt_id:
        canonical_id = attempt.duplicate_of_attempt_id
        related = db.query(Attempt).options(
            joinedload(Attempt.student),
            joinedload(Attempt.score)
        ).filter(
            (Attempt.id == canonical_id) |
            (Attempt.duplicate_of_attempt_id == canonical_id)
        ).all()
        duplicate_thread = [
            {
                "id": str(r.id),
                "student_name": r.student.full_name if r.student else None,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "score": float(r.score.score) if r.score else None,
                "is_canonical": r.duplicate_of_attempt_id is None
            }
            for r in related
        ]
    else:
        duplicates = db.query(Attempt).options(
            joinedload(Attempt.student),
            joinedload(Attempt.score)
        ).filter(
            Attempt.duplicate_of_attempt_id == attempt.id
        ).all()
        if duplicates:
            duplicate_thread = [
                {
                    "id": str(attempt.id),
                    "student_name": attempt.student.full_name if attempt.student else None,
                    "status": attempt.status,
                    "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
                    "score": float(attempt.score.score) if attempt.score else None,
                    "is_canonical": True
                }
            ] + [
                {
                    "id": str(d.id),
                    "student_name": d.student.full_name if d.student else None,
                    "status": d.status,
                    "started_at": d.started_at.isoformat() if d.started_at else None,
                    "score": float(d.score.score) if d.score else None,
                    "is_canonical": False
                }
                for d in duplicates
            ]
    
    result["duplicate_thread"] = duplicate_thread
    return result


@router.post("/api/attempts/{attempt_id}/recompute")
def recompute_score(attempt_id: str, db: Session = Depends(get_db)):
    """Recompute the score for a specific attempt."""
    start_time = time.time()
    
    attempt = db.query(Attempt).options(
        joinedload(Attempt.test),
        joinedload(Attempt.score)
    ).filter(Attempt.id == attempt_id).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    if attempt.status == "DEDUPED":
        raise HTTPException(
            status_code=400,
            detail="Cannot recompute score for a deduplicated attempt."
        )
    
    score = compute_score(attempt, attempt.test, db)
    
    duration_ms = (time.time() - start_time) * 1000
    log_with_context(logger, "INFO",
        "Score recomputed for attempt {}: {}".format(attempt_id, float(score.score)),
        context={"attempt_id": attempt_id},
        extra_data={"duration_ms": round(duration_ms, 2)})
    
    return {
        "message": "Score recomputed successfully",
        "attempt_id": attempt_id,
        "score": {
            "correct": score.correct,
            "wrong": score.wrong,
            "skipped": score.skipped,
            "accuracy": float(score.accuracy),
            "net_correct": score.net_correct,
            "score": float(score.score),
            "computed_at": score.computed_at.isoformat(),
            "explanation": _parse_json(score.explanation)
        }
    }


@router.post("/api/attempts/{attempt_id}/flag")
def flag_attempt(attempt_id: str, request: FlagRequest, db: Session = Depends(get_db)):
    """Create a flag on an attempt with a reason."""
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    if not request.reason.strip():
        raise HTTPException(status_code=400, detail="Flag reason cannot be empty")
    
    flag = Flag(
        id=str(uuid.uuid4()),
        attempt_id=attempt.id,
        reason=request.reason.strip(),
        created_at=datetime.now(timezone.utc)
    )
    db.add(flag)
    
    attempt.status = "FLAGGED"
    
    db.commit()
    db.refresh(flag)
    
    log_with_context(logger, "INFO",
        "Attempt {} flagged: {}".format(attempt_id, request.reason[:100]),
        context={"attempt_id": attempt_id, "flag_id": str(flag.id)})
    
    return FlagResponse(
        id=str(flag.id),
        attempt_id=str(attempt.id),
        reason=flag.reason,
        created_at=flag.created_at.isoformat()
    )
