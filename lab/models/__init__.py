from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    message: str


class Document(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    name: str
    status: str = 'IN-PROCESS'
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


class ExtractDocument(BaseModel):
    document_id: UUID
    document_json: dict = {}


class JsonDocument(BaseModel):
    json_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    document_json: dict = {}


class JsonDocumentResponse(JsonDocument):
    rating: int
    evaluated_document_json: dict | None = {}
    created_at: datetime


class JsonDocumentEvaluation(BaseModel):
    document_id: UUID
    json_id: UUID
    rating: int
    evaluated_document_json: dict | None = {}
