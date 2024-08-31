from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    message: str


class Document(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    name: str
    status: str = 'IN-PROCESS'
    created_at: datetime = Field(default_factory=datetime.now)
