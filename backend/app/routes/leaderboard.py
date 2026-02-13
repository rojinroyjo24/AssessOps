"""
Leaderboard API route - ranked student performance view.

Ranks students by their best attempt for a given test using these criteria:
1. Total score (highest first)
2. Accuracy (highest first, as tiebreaker)
3. Net correct answers (highest first, as secondary tiebreaker)
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.attempt import Attempt
from app.models.attempt_score import AttemptScore
from app.models.test import Test
from app.models.student import Student
from app.logging_config import get_logger, log_with_context

router = APIRouter()
logger = get_logger("http")


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


@router.get("/api/leaderboard")
def get_leaderboard(
    test_id: Optional[str] = Query(None, description="Test ID to show leaderboard for"),
    db: Session = Depends(get_db)
):
    """
    Get ranked student leaderboard for a specific test.
    """
    # Get all available tests for the dropdown selector
    all_tests = db.query(Test).all()
    tests_list = [
        {"id": str(t.id), "name": t.name}
        for t in all_tests
    ]
    
    # If no test specified, use the first one
    if not test_id and all_tests:
        test_id = str(all_tests[0].id)
    
    if not test_id:
        return {
            "tests": tests_list,
            "test_id": None,
            "leaderboard": []
        }
    
    # Get all scored attempts for this test, with their scores
    attempts = db.query(Attempt).options(
        joinedload(Attempt.student),
        joinedload(Attempt.score)
    ).filter(
        Attempt.test_id == test_id,
        Attempt.status == "SCORED"
    ).all()
    
    # Group by student|keep only best attempt per student
    best_attempts = {}
    for attempt in attempts:
        student_id = str(attempt.student_id)
        if not attempt.score:
            continue
        
        current_score = float(attempt.score.score)
        current_accuracy = float(attempt.score.accuracy)
        current_net = attempt.score.net_correct
        
        if student_id not in best_attempts:
            best_attempts[student_id] = attempt
        else:
            existing = best_attempts[student_id]
            existing_score = float(existing.score.score)
            existing_accuracy = float(existing.score.accuracy)
            existing_net = existing.score.net_correct
            
            # Replace if better score, or same score but better accuracy,
            # or same score+accuracy but better net_correct
            if (current_score > existing_score or
                (current_score == existing_score and current_accuracy > existing_accuracy) or
                (current_score == existing_score and current_accuracy == existing_accuracy and
                 current_net > existing_net)):
                best_attempts[student_id] = attempt
    
    # Sort by score DESC, accuracy DESC, net_correct DESC
    sorted_attempts = sorted(
        best_attempts.values(),
        key=lambda a: (
            float(a.score.score),
            float(a.score.accuracy),
            a.score.net_correct
        ),
        reverse=True
    )
    
    # Build leaderboard with ranks
    leaderboard = []
    for rank, attempt in enumerate(sorted_attempts, 1):
        leaderboard.append({
            "rank": rank,
            "is_top_3": rank <= 3,
            "attempt_id": str(attempt.id),
            "student": {
                "id": str(attempt.student.id),
                "full_name": attempt.student.full_name,
                "email": attempt.student.email,
                "phone": attempt.student.phone
            },
            "score": float(attempt.score.score),
            "accuracy": float(attempt.score.accuracy),
            "net_correct": attempt.score.net_correct,
            "correct": attempt.score.correct,
            "wrong": attempt.score.wrong,
            "skipped": attempt.score.skipped,
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None
        })
    
    log_with_context(logger, "INFO",
        "Leaderboard generated: {} students for test {}".format(len(leaderboard), test_id),
        extra_data={"test_id": test_id, "entries": len(leaderboard)})
    
    return {
        "tests": tests_list,
        "test_id": test_id,
        "leaderboard": leaderboard
    }
