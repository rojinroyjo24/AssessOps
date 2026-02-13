"""
Student model - represents students taking assessments.

Each student is uniquely identified by UUID. Students are linked to
attempts via the student_id foreign key in the attempts table.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, DateTime, String
from sqlalchemy.orm import relationship
from app.database import Base


class Student(Base):
    """
    SQLAlchemy model for the students table.
    
    Stores basic student information. Students can be identified by
    normalized email or phone for deduplication purposes.
    """
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
                doc="Unique student identifier")
    full_name = Column(Text, nullable=False,
                       doc="Student's full name as provided by coaching centre")
    email = Column(Text, nullable=True,
                   doc="Student email (nullable - some students don't provide email)")
    phone = Column(Text, nullable=True,
                   doc="Student phone number (nullable - used as fallback identity)")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        doc="Timestamp when student record was created")

    # Relationship: one student has many attempts
    attempts = relationship("Attempt", back_populates="student")

    def __repr__(self):
        return f"<Student(id={self.id}, name='{self.full_name}', email='{self.email}')>"
