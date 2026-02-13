"""
Deduplication Service - Smart duplicate detection for assessment attempts.

Implements the core deduplication logic:
1. Student identity matching (normalized email or phone fallback)
2. Same test detection
3. Time proximity check (within 7-minute window)
4. Answer similarity calculation (>= 92% threshold)

IMPORTANT: Answer similarity is computed WITHOUT any fuzzy matching libraries.
We use a simple set intersection approach: count matching answers for questions
present in both attempts, divided by total compared questions.

Design Decision: The 92% threshold was chosen because minor UI glitches or 
network retries can cause re-submissions with 1-2 changed answers (e.g., a
student clicking a different option while the form resubmits). A threshold
below 90% risks missing true duplicates, while above 95% might be too strict.
"""

import re
import json
from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.attempt import Attempt
from app.logging_config import get_logger, log_with_context

# Channel logger for deduplication operations
logger = get_logger("dedup")

# ──────────────────────────────────────────────────────────────
# Configuration constants
# ──────────────────────────────────────────────────────────────
DUPLICATE_TIME_WINDOW_MINUTES = 7    # Max time difference between duplicate attempts
ANSWER_SIMILARITY_THRESHOLD = 0.92   # 92% answer match required for duplicate


def _parse_json(value):
    """Parse JSON from string or return as-is if already dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def normalize_email(email: str) -> str:
    """
    Normalize an email address for identity matching.
    
    Rules applied:
    1. Convert to lowercase
    2. For Gmail addresses: remove '+alias' portion before @
       (e.g., john.doe+test@gmail.com → john.doe@gmail.com)
    
    This handles the common case where coaching centres submit
    the same student with different Gmail aliases.
    
    Args:
        email: Raw email string
        
    Returns:
        Normalized email string
    """
    if not email:
        return None
    
    email = email.strip().lower()
    
    # Handle Gmail aliases: remove everything after '+' before '@'
    # Gmail ignores the +alias portion when delivering mail,
    # so john+test@gmail.com and john@gmail.com are the same person
    if "@gmail.com" in email:
        local_part, domain = email.split("@", 1)
        if "+" in local_part:
            local_part = local_part.split("+")[0]
        email = f"{local_part}@{domain}"
    
    return email


def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number by extracting only digits.
    
    Removes all non-digit characters (spaces, dashes, parentheses, etc.)
    to create a consistent format for identity matching.
    
    Examples:
        "91-7654-321098" → "917654321098"
        "91 7654 321098" → "917654321098"
        "+91 (765) 432-1098" → "917654321098"
    
    Args:
        phone: Raw phone string
        
    Returns:
        Digits-only phone string, or None if empty
    """
    if not phone:
        return None
    # Strip all non-digit characters using regex
    return re.sub(r'\D', '', phone)


def get_student_identity(email: str, phone: str) -> tuple:
    """
    Determine the canonical identity for a student.
    
    Priority: normalized email first, phone as fallback.
    Returns a tuple of (identity_type, identity_value) for comparison.
    
    Args:
        email: Student email (may be None)
        phone: Student phone (may be None)
        
    Returns:
        Tuple of (type, value) e.g., ("email", "john@gmail.com") or ("phone", "917654321098")
    """
    normalized_email = normalize_email(email)
    if normalized_email:
        return ("email", normalized_email)
    
    normalized_phone = normalize_phone(phone)
    if normalized_phone:
        return ("phone", normalized_phone)
    
    # Neither email nor phone available - cannot identify student
    return ("unknown", None)


def calculate_answer_similarity(answers1: dict, answers2: dict) -> float:
    """
    Calculate the similarity between two answer sets WITHOUT fuzzy libraries.
    
    Algorithm:
    1. Find questions present in BOTH attempts (intersection of question numbers)
    2. Count how many of those questions have the same answer
    3. Similarity = matching_answers / total_compared_questions
    
    This approach handles partial submissions naturally - we only compare
    questions that both students answered.
    
    Args:
        answers1: First attempt's answers dict {question_no: answer}
        answers2: Second attempt's answers dict {question_no: answer}
        
    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    if not answers1 or not answers2:
        return 0.0
    
    # Find questions that exist in both answer sets
    common_questions = set(answers1.keys()) & set(answers2.keys())
    
    if not common_questions:
        return 0.0
    
    # Count matching answers for common questions
    matching = sum(
        1 for q in common_questions
        if str(answers1[q]).upper().strip() == str(answers2[q]).upper().strip()
    )
    
    similarity = matching / len(common_questions)
    return similarity


def check_duplicate(new_attempt_data: dict, existing_attempts: list,
                    test_id_internal: str) -> dict:
    """
    Check if a new attempt is a duplicate of any existing attempt.
    
    Duplicate Detection Rules (ALL must be met):
    1. Same student identity (normalized email or phone)
    2. Same test_id
    3. started_at within 7 minutes of each other
    4. Answer similarity >= 92%
    
    Args:
        new_attempt_data: Dict with the new attempt's data (email, phone, answers, started_at)
        existing_attempts: List of existing Attempt ORM objects for this test+student
        test_id_internal: Internal UUID of the test
        
    Returns:
        Dict with 'is_duplicate' bool and optional 'canonical_attempt_id'
    """
    new_identity = get_student_identity(
        new_attempt_data.get("email"),
        new_attempt_data.get("phone")
    )
    
    if new_identity[1] is None:
        log_with_context(logger, "WARNING", "Cannot determine student identity for dedup check",
                        context={"test_id": str(test_id_internal)})
        return {"is_duplicate": False, "canonical_attempt_id": None}
    
    new_started_at = new_attempt_data.get("started_at")
    new_answers = new_attempt_data.get("answers", {})
    
    for existing in existing_attempts:
        # Rule 1: Same student identity (already filtered by test_id)
        existing_identity = get_student_identity(
            existing.student.email if existing.student else None,
            existing.student.phone if existing.student else None
        )
        
        if new_identity != existing_identity:
            continue
        
        # Rule 3: Time proximity check (within 7 minutes)
        time_diff = 0
        if existing.started_at and new_started_at:
            # Normalize both to naive UTC to avoid offset-naive vs offset-aware errors
            _new_ts = new_started_at.replace(tzinfo=None) if new_started_at.tzinfo else new_started_at
            _ext_ts = existing.started_at.replace(tzinfo=None) if existing.started_at.tzinfo else existing.started_at
            time_diff = abs((_new_ts - _ext_ts).total_seconds())
            if time_diff > DUPLICATE_TIME_WINDOW_MINUTES * 60:
                log_with_context(logger, "DEBUG",
                    "Time difference {:.0f}s exceeds {}min window".format(
                        time_diff, DUPLICATE_TIME_WINDOW_MINUTES),
                    context={"existing_attempt_id": str(existing.id)})
                continue
        
        # Rule 4: Answer similarity check (>= 92%)
        # Parse existing answers from JSON string if needed
        existing_answers = _parse_json(existing.answers) if existing.answers else {}
        similarity = calculate_answer_similarity(new_answers, existing_answers)
        
        log_with_context(logger, "DEBUG",
            "Answer similarity: {:.4f} (threshold: {})".format(
                similarity, ANSWER_SIMILARITY_THRESHOLD),
            context={
                "existing_attempt_id": str(existing.id),
                "test_id": str(test_id_internal)
            },
            extra_data={"similarity": similarity, "threshold": ANSWER_SIMILARITY_THRESHOLD})
        
        if similarity >= ANSWER_SIMILARITY_THRESHOLD:
            log_with_context(logger, "INFO",
                "Duplicate detected! Similarity={:.2%}, time_diff={:.0f}s".format(
                    similarity, time_diff),
                context={
                    "canonical_attempt_id": str(existing.id),
                    "test_id": str(test_id_internal)
                })
            return {"is_duplicate": True, "canonical_attempt_id": existing.id}
    
    return {"is_duplicate": False, "canonical_attempt_id": None}
