from uuid import UUID

from fastapi import APIRouter

from lab.models import Message

from ..dao.dao_documents import list_llm_documents, list_sigle_llm_document
from ..dao.dao_openai import fetch_document

router = APIRouter(prefix='/open-ai', tags=['OpenAI'])


@router.post('/document/{document_id}', response_model=Message)
def load_single_document(document_id: UUID):
    documents = list_sigle_llm_document()
    fetch_document(documents)
    return {'message': 'dados extraidos'}


@router.post('/document', response_model=Message)
def load_document():
    document = list_llm_documents()
    fetch_document(document)
    return {'message': 'dados extraidos'}
