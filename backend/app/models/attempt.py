"""
Attempt model - represents a single student assessment attempt.

This is the central entity in the platform. Each attempt contains:
- The student's answers as JSON (question_no -> answer)
- The raw event payload for audit trail
- Status tracking through the processing pipeline
- Optional duplicate linking for deduplication
"""

import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Text, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from app.database import Base


class Attempt(Base):
    """
    SQLAlchemy model for the attempts table.
    
    Tracks the lifecycle of an assessment attempt through statuses:
    - INGESTED: Raw event received and stored
    - DEDUPED: Identified as duplicate of another attempt
    - SCORED: Successfully scored (canonical, non-duplicate attempt)
    - FLAGGED: Manually flagged for review
    """
    __tablename__ = "attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
                doc="Unique attempt identifier")
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False,
                        doc="Reference to the student who made this attempt")
    test_id = Column(String(36), ForeignKey("tests.id"), nullable=False,
                     doc="Reference to the test being attempted")
    source_event_id = Column(Text, nullable=True,
                             doc="Original event ID from the coaching centre's system")
    started_at = Column(DateTime, nullable=False,
                        doc="When the student started the test")
    submitted_at = Column(DateTime, nullable=True,
                          doc="When the student submitted (NULL for partial submissions)")
    answers = Column(Text, nullable=False, default="{}",
                     doc="Student answers as JSON: {question_no: 'A'|'B'|'C'|'D'|'SKIP'}")
    raw_payload = Column(Text, nullable=True,
                         doc="Complete raw event payload as JSON for audit/debugging")
    status = Column(Text, nullable=False, default="INGESTED",
                    doc="Processing status: INGESTED | DEDUPED | SCORED | FLAGGED")
    duplicate_of_attempt_id = Column(String(36), ForeignKey("attempts.id"), nullable=True,
                                     doc="If this is a duplicate, points to the canonical attempt")

    # Relationships
    student = relationship("Student", back_populates="attempts")
    test = relationship("Test", back_populates="attempts")
    score = relationship("AttemptScore", back_populates="attempt", uselist=False)
    flags = relationship("Flag", back_populates="attempt")
    # Self-referential relationship for duplicate chains
    canonical_attempt = relationship("Attempt", remote_side="Attempt.id", foreign_keys=[duplicate_of_attempt_id])

    # Database indexes for common query patterns
    __table_args__ = (
        Index("ix_attempts_student_id", "student_id"),
        Index("ix_attempts_test_id", "test_id"),
        Index("ix_attempts_status", "status"),
        Index("ix_attempts_started_at", "started_at"),
        Index("ix_attempts_source_event_id", "source_event_id"),
    )

    @property
    def answers_dict(self):
        """Parse answers JSON string to dict."""
        if isinstance(self.answers, dict):
            return self.answers
        try:
            return json.loads(self.answers) if self.answers else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def raw_payload_dict(self):
        """Parse raw_payload JSON string to dict."""
        if isinstance(self.raw_payload, dict):
            return self.raw_payload
        try:
            return json.loads(self.raw_payload) if self.raw_payload else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self):
        return f"<Attempt(id={self.id}, student={self.student_id}, test={self.test_id}, status='{self.status}')>"
