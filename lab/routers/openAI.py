from uuid import UUID

from fastapi import APIRouter, HTTPException

from lab.models import (
    JsonDocument,
    JsonDocumentEvaluation,
    JsonDocumentResponse,
    Message,
)

from ..dao.dao_documents import select_llm_documents
from ..dao.dao_openai import (
    fetch_document,
    select_dopenai_json,
    select_single_dopenai_json,
    update_openai_json_documents,
)

router = APIRouter(prefix='/open-ai', tags=['OpenAI'])


@router.post('/document/{document_id}', response_model=JsonDocument)
def load_single_document(document_id: UUID):
    document = select_llm_documents(document_id)
    document = fetch_document(document)[0]
    return document


@router.post('/document', response_model=list[JsonDocument])
def load_document():
    documents = select_llm_documents()
    documents = fetch_document(documents)
    return documents


@router.get('/document', response_model=list[JsonDocumentResponse])
def list_json_documents():
    documents = select_dopenai_json()
    if not documents:
        raise HTTPException(status_code=404, detail='Documents not found')
    return documents


@router.get('/document/{document_id}', response_model=JsonDocumentResponse)
def list_single_json_documents(document_id: UUID):
    document = select_single_dopenai_json(document_id)
    return document


@router.put('/document', response_model=Message)
def update_json_documents(JsonDocumentEvaluation: JsonDocumentEvaluation):
    update_openai_json_documents(JsonDocumentEvaluation)
    return {'message': 'OK'}
