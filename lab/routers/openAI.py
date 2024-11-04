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
    update_openai_json_documents,
)

router = APIRouter(prefix='/open-ai', tags=['OpenAI'])


@router.post('/document', response_model=list[JsonDocument])
@router.post('/document/{document_id}', response_model=JsonDocument)
def load_documents(document_id: UUID = None):
    documents = select_llm_documents(document_id)
    documents = fetch_document(documents)

    if document_id:
        return documents[0]
    return documents


@router.get('/document', response_model=list[JsonDocumentResponse])
@router.get('/document/{document_id}', response_model=JsonDocumentResponse)
def list_json_documents(document_id: UUID = None):
    documents = select_dopenai_json(document_id)

    if not documents:
        raise HTTPException(status_code=404, detail='Documents not found')

    if document_id:
        return documents[0]
    return documents


@router.put('/document', response_model=Message)
def update_json_documents(JsonDocumentEvaluation: JsonDocumentEvaluation):
    update_openai_json_documents(JsonDocumentEvaluation)
    return {'message': 'OK'}
