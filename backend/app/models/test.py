"""
Test model - represents assessment tests created by coaching centres.

Each test defines its marking scheme (correct/wrong/skip points) as JSON,
allowing flexible marking configurations per test.
"""

import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Text, Integer, DateTime, String
from sqlalchemy.orm import relationship
from app.database import Base


class Test(Base):
    """
    SQLAlchemy model for the tests table.
    
    Stores test metadata including the negative marking scheme.
    The negative_marking field holds JSON: {"correct": 4, "wrong": -1, "skip": 0}
    """
    __tablename__ = "tests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
                doc="Unique test identifier")
    name = Column(Text, nullable=False,
                  doc="Test name/title")
    max_marks = Column(Integer, nullable=False, default=400,
                       doc="Maximum possible marks for this test")
    negative_marking = Column(Text, nullable=False,
                              default='{"correct": 4, "wrong": -1, "skip": 0}',
                              doc="Marking scheme as JSON string")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        doc="Timestamp when test was created")

    # Relationship: one test has many attempts
    attempts = relationship("Attempt", back_populates="test")

    @property
    def marking_scheme(self):
        """Parse the negative_marking JSON string into a dict."""
        if isinstance(self.negative_marking, dict):
            return self.negative_marking
        try:
            return json.loads(self.negative_marking)
        except (json.JSONDecodeError, TypeError):
            return {"correct": 4, "wrong": -1, "skip": 0}

    def __repr__(self):
        return f"<Test(id={self.id}, name='{self.name}', max_marks={self.max_marks})>"
