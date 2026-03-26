from sqlmodel import SQLModel, Field
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey

class Resume(SQLModel, table=True):

    __tablename__ = "resumes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    file_name: str
    raw_text: Optional[str] = None
    parsed_json: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), index=True))
