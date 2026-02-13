"""
AttemptScore model - stores computed scores for assessment attempts.

Each scored attempt gets exactly one AttemptScore record containing:
- Raw counts (correct, wrong, skipped)
- Computed metrics (accuracy, net_correct, score)
- Detailed explanation breakdown as JSON
"""

import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text, String
from sqlalchemy.orm import relationship
from app.database import Base


class AttemptScore(Base):
    """
    SQLAlchemy model for the attempt_scores table.
    
    One-to-one relationship with Attempt (attempt_id is both PK and FK).
    The explanation field stores a detailed scoring breakdown as JSON.
    """
    __tablename__ = "attempt_scores"

    attempt_id = Column(String(36), ForeignKey("attempts.id"), primary_key=True,
                        doc="Reference to the scored attempt (also serves as PK)")
    correct = Column(Integer, nullable=False, default=0,
                     doc="Number of correctly answered questions")
    wrong = Column(Integer, nullable=False, default=0,
                   doc="Number of incorrectly answered questions")
    skipped = Column(Integer, nullable=False, default=0,
                     doc="Number of skipped questions")
    accuracy = Column(Float, nullable=False, default=0,
                      doc="Accuracy percentage: (correct / (correct + wrong)) * 100")
    net_correct = Column(Integer, nullable=False, default=0,
                         doc="Net correct answers: correct - wrong")
    score = Column(Float, nullable=False, default=0,
                   doc="Final score with negative marking applied")
    computed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         doc="When this score was computed/last recomputed")
    explanation = Column(Text, nullable=True,
                         doc="Detailed scoring breakdown as JSON string")

    # One-to-one relationship back to Attempt
    attempt = relationship("Attempt", back_populates="score")

    @property
    def explanation_dict(self):
        """Parse explanation JSON string to dict."""
        if isinstance(self.explanation, dict):
            return self.explanation
        try:
            return json.loads(self.explanation) if self.explanation else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self):
        return f"<AttemptScore(attempt={self.attempt_id}, score={self.score}, accuracy={self.accuracy}%)>"
