"""
Scoring Service - Computes marks with negative marking for assessment attempts.

Implements the scoring formula:
1. Count answers by type (correct, wrong, skipped)
2. accuracy = (correct / (correct + wrong)) * 100  (0 if no answers)
3. net_correct = correct - wrong
4. score = (correct * marking.correct) + (wrong * marking.wrong) + (skipped * marking.skip)
"""

import time
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.attempt import Attempt
from app.models.attempt_score import AttemptScore
from app.models.test import Test
from app.logging_config import get_logger, log_with_context

# Channel logger for scoring operations
logger = get_logger("scoring")


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


def compute_score(attempt: Attempt, test: Test, db: Session,
                  answer_key: dict = None) -> AttemptScore:
    """
    Compute the score for a given attempt using the test's marking scheme.
    
    Args:
        attempt: The Attempt ORM object to score
        test: The Test ORM object with marking scheme
        db: Database session for persistence
        answer_key: Optional dict mapping question_no -> correct_answer
    
    Returns:
        AttemptScore ORM object with computed values
    """
    start_time = time.time()
    
    # Get the marking scheme from the test configuration
    marking = _parse_json(test.negative_marking)
    if not marking:
        marking = {"correct": 4, "wrong": -1, "skip": 0}
    
    answers = _parse_json(attempt.answers)
    
    # Categorize answers
    correct_count = 0
    wrong_count = 0
    skipped_count = 0
    
    if answer_key:
        # Score against provided answer key
        for question_no, student_answer in answers.items():
            student_ans = str(student_answer).upper().strip()
            if student_ans == "SKIP":
                skipped_count += 1
            elif question_no in answer_key:
                correct_ans = str(answer_key[question_no]).upper().strip()
                if student_ans == correct_ans:
                    correct_count += 1
                else:
                    wrong_count += 1
            else:
                wrong_count += 1
    else:
        # No answer key - use deterministic default key for demo
        default_answers = ["A", "B", "C", "D"]
        for question_no, student_answer in answers.items():
            student_ans = str(student_answer).upper().strip()
            if student_ans == "SKIP":
                skipped_count += 1
            else:
                try:
                    q_num = int(question_no)
                    expected = default_answers[(q_num - 1) % 4]
                except (ValueError, IndexError):
                    expected = "A"
                
                if student_ans == expected:
                    correct_count += 1
                else:
                    wrong_count += 1
    
    # Calculate derived metrics
    total_answered = correct_count + wrong_count
    accuracy = (correct_count / total_answered * 100) if total_answered > 0 else 0.0
    net_correct = correct_count - wrong_count
    
    # Apply marking scheme to compute final score
    correct_points = correct_count * marking.get("correct", 4)
    wrong_points = wrong_count * marking.get("wrong", -1)
    skip_points = skipped_count * marking.get("skip", 0)
    total_score = correct_points + wrong_points + skip_points
    
    # Build detailed explanation JSON for transparency
    explanation = {
        "marking_scheme": marking,
        "counts": {
            "correct": correct_count,
            "wrong": wrong_count,
            "skipped": skipped_count
        },
        "breakdown": {
            "correct_points": correct_points,
            "wrong_points": wrong_points,
            "skip_points": skip_points,
            "total": total_score
        }
    }
    
    # Create or update the AttemptScore record
    existing_score = db.query(AttemptScore).filter(
        AttemptScore.attempt_id == attempt.id
    ).first()
    
    if existing_score:
        # Update existing score (recomputation)
        existing_score.correct = correct_count
        existing_score.wrong = wrong_count
        existing_score.skipped = skipped_count
        existing_score.accuracy = accuracy
        existing_score.net_correct = net_correct
        existing_score.score = total_score
        existing_score.computed_at = datetime.now(timezone.utc)
        existing_score.explanation = json.dumps(explanation)
        score_record = existing_score
    else:
        # Create new score record
        score_record = AttemptScore(
            attempt_id=attempt.id,
            correct=correct_count,
            wrong=wrong_count,
            skipped=skipped_count,
            accuracy=accuracy,
            net_correct=net_correct,
            score=total_score,
            computed_at=datetime.now(timezone.utc),
            explanation=json.dumps(explanation)
        )
        db.add(score_record)
    
    # Update attempt status to SCORED
    attempt.status = "SCORED"
    
    db.commit()
    db.refresh(score_record)
    
    # Calculate computation duration for performance monitoring
    duration_ms = (time.time() - start_time) * 1000
    
    log_with_context(logger, "INFO",
        "Score computed: {} (correct={}, wrong={}, skipped={}, accuracy={:.2f}%)".format(
            total_score, correct_count, wrong_count, skipped_count, accuracy),
        context={
            "attempt_id": str(attempt.id),
            "student_id": str(attempt.student_id),
            "test_id": str(attempt.test_id)
        },
        extra_data={
            "duration_ms": round(duration_ms, 2),
            "score": float(total_score),
            "accuracy": round(accuracy, 4)
        })
    
    return score_record
