from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter

from ..dao import dao_ollama
from ..models import Message

router = APIRouter(tags=['Ollama'])


@router.post(
    '/ollama/{document_id}',
    response_model=Message,
    status_code=HTTPStatus.CREATED,
)
def create_parameter(document_id: UUID):
    document = dao_ollama.extract_data(document_id)
    return {'message': 'OK'}