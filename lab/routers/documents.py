import os
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from lab.models import (
    BaseDocument,
    Document,
    DocumentData,
    EvaluateDocumentData,
    Message,
)

from ..celery import celery
from ..dao import dao_documents, dao_ollama

router = APIRouter(tags=['Documents'])


@celery.task()
def celery_add_database_document(document_id):
    chunks = dao_ollama.embed_document(document_id)

    dao_ollama.get_patient(document_id)
    dao_ollama.get_date(document_id)

    dao_documents.extract_data(document_id)

    dao_documents.att_status(document_id, chunks)
    return {'message': 'OK'}


@router.post(
    '/document',
    status_code=HTTPStatus.CREATED,
    response_model=list[BaseDocument],
)
def upload_files(files: list[UploadFile] = File(...)):
    documents = []

    for file in files:
        document = dao_documents.add_database_document(file.filename)

        with open(f'documents/{document.document_id}.pdf', 'wb') as buffer:
            buffer.write(file.file.read())
        celery_add_database_document.delay(document.document_id)
        documents.append(document)
    return documents


@router.get('/document', response_model=list[BaseDocument])
def list_files():
    documents = dao_documents.list_database_documents()
    if not documents:
        raise HTTPException(status_code=404, detail='File not found')
    return documents


@router.get(
    '/document/file/{document_id}',
    response_class=FileResponse,
)
def get_file(document_id: UUID):
    file_path = f'documents/{document_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)


@router.get('/document/{document_id}', response_model=Document)
def get_document(document_id: UUID):
    document = dao_documents.get_document(document_id)
    return document


@router.delete(
    '/document/{document_id}',
    response_model=Message,
)
def delete_file(document_id: UUID):
    file_path = f'documents/{document_id}.pdf'

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    dao_documents.delete_database_document(document_id)
    dao_ollama.remove_from_chroma(document_id)
    os.remove(file_path)

    return {'message': 'Document deleted!'}


@router.post(
    '/document/data/{document_id}',
    response_model=DocumentData,
    status_code=HTTPStatus.CREATED,
)
def extract_data(document_id: UUID):
    structured_data = dao_ollama.extract_data(document_id)
    return structured_data


@router.put(
    '/document/data',
    response_model=Message,
    status_code=HTTPStatus.OK,
)
def update_data(evaluated_data: EvaluateDocumentData):
    dao_documents.update_data(evaluated_data)
    return {'message': 'OK'}
