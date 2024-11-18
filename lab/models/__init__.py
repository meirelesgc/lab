from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator


class Message(BaseModel):
    message: str


class BaseParameter(BaseModel):
    parameter: str
    synonyms: list = []


class Parameter(BaseParameter):
    parameter_id: UUID = Field(default_factory=uuid4)


class Patient(BaseModel):
    patient_id: UUID = Field(default_factory=uuid4)
    name: str


class BaseDocument(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    name: str
    status: str = 'IN-PROCESS'
    created_at: datetime = Field(default_factory=datetime.now)


class Document(BaseDocument):
    patients: list[Patient] = []
    unverified_patient: list[Patient] = []
    document_date: Optional[datetime]
    document_data: dict = Field(default_factory=dict)


class DocumentData(BaseModel):
    data_id: UUID = Field(default_factory=uuid4)
    document_data: Optional[dict]


class EvaluateDocumentData(DocumentData):
    document_id: UUID
    rating: int
    patient_id: list[UUID] | UUID
    document_date: datetime

    @validator('patient_id', pre=True, always=True)
    def validate_patient_id(cls, value):
        if len(value) > 1:
            raise ValueError('patient_id must contain only one UUID.')
        return value[0] if value else None


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    user_id: UUID
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)
