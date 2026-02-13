"""
Flag model - stores manual flags/annotations on attempts.

Flags are created when reviewers identify suspicious or noteworthy
attempts. Each flag records a reason and timestamp.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class Flag(Base):
    """
    SQLAlchemy model for the flags table.
    
    Multiple flags can exist per attempt (e.g., flagged for different reasons
    by different reviewers). Creating a flag also updates the attempt status
    to FLAGGED.
    """
    __tablename__ = "flags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
                doc="Unique flag identifier")
    attempt_id = Column(String(36), ForeignKey("attempts.id"), nullable=False,
                        doc="Reference to the flagged attempt")
    reason = Column(Text, nullable=False,
                    doc="Human-readable reason for flagging")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        doc="When this flag was created")

    # Relationship back to Attempt
    attempt = relationship("Attempt", back_populates="flags")

    def __repr__(self):
        return f"<Flag(id={self.id}, attempt={self.attempt_id}, reason='{self.reason[:50]}')>"
