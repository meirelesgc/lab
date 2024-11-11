from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    message: str


class Document(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    name: str
    status: str = "IN-PROCESS"
    created_at: datetime = Field(default_factory=datetime.now)


class DocumentMetadata(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    document_date: Optional[datetime] = None


class BaseParameter(BaseModel):
    parameter: str
    synonyms: list = []


class Parameter(BaseParameter):
    parameter_id: UUID = Field(default_factory=uuid4)


class Patient(BaseModel):
    patient_id: UUID = Field(default_factory=uuid4)
    name: str


class StructuredData(BaseModel):
    document_id: UUID
    structured_data: dict | None
