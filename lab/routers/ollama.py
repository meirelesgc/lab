from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter

from ..dao import dao_ollama
from ..models import DocumentData, EvaluateDocumentData, Message

router = APIRouter(tags=["Ollama"])


@router.post(
    "/ollama/{document_id}",
    response_model=DocumentData,
    status_code=HTTPStatus.CREATED,
)
def create_parameter(document_id: UUID):
    structured_data = dao_ollama.extract_data(document_id)
    return structured_data


@router.post(
    "/ollama/evaluate",
    response_model=Message,
    status_code=HTTPStatus.CREATED,
)
def create_parameter(document_data: EvaluateDocumentData):
    structured_data = dao_ollama.evaluate_data(document_data)
    return {"message": "OK"}
