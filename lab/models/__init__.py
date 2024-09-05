from datetime import datetime
from typing import Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    message: str


class Document(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    name: str
    status: str = 'IN-PROCESS'
    created_at: datetime = Field(default_factory=datetime.now)


class Parameter(BaseModel):
    parameter_id: UUID = Field(default_factory=uuid4)
    parameter: str
    synonyms: list = []


class JsonDocument(BaseModel):
    json_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    document_json: Dict = {}


class JsonDocumentResponse(JsonDocument):
    rating: int
    evaluated_document_json: Dict
    created_at: datetime


class JsonDocumentEvaluation(BaseModel):
    document_id: UUID
    json_id: UUID
    rating: int
    evaluated_document_json: Dict
