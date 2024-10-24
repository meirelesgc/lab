import os
from http import HTTPStatus
from uuid import UUID

from celery import Celery
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from lab.models import Document, Message

from ..config import settings
from ..dao import dao_documents, dao_ollama

router = APIRouter(tags=['Documents'])
'pyamqp://guest@localhost//'
celery = Celery(
    broker=settings.BROKER, broker_connection_retry_on_startup=True
)


@celery.task()
def celery_add_database_text(document_id):
    dao_ollama.add_database_text(document_id)
    return {'message': 'Texto limpo'}


@celery.task()
def celery_add_database_metadata(document_id):
    # dao_ollama.add_database_metadata(document_id)
    return {'message': 'Metadados Extraidos'}


@router.post(
    '/file', status_code=HTTPStatus.CREATED, response_model=list[Document]
)
def upload_files(files: list[UploadFile] = File(...)):
    documents = []

    for file in files:
        # Registrar que foi salvo e gerar um identificador
        document = dao_documents.add_database_document(file.filename)

        # Salvar o arquivo localmente
        with open(f'documents/{document.document_id}.pdf', 'wb') as buffer:
            buffer.write(file.file.read())

        # Etapa dois do registro
        celery_add_database_text.delay(document.document_id)
        celery_add_database_metadata.delay(document.document_id)

        documents.append(document)

    # Concluir a operação
    return documents


@router.get('/file', response_model=list[Document])
def list_files():
    documents = dao_documents.list_database_documents()
    if not documents:
        raise HTTPException(status_code=404, detail='File not found')
    return documents


@router.get(
    '/file/{document_id}',
    response_class=FileResponse,
)
def get_file(document_id: UUID):
    file_path = f'documents/{document_id}.pdf'

    # Verifica se o arquivo existe
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    return FileResponse(file_path)


@router.delete(
    '/file/{document_id}',
    response_model=Message,
)
def delete_file(document_id: UUID):
    file_path = f'documents/{document_id}.pdf'

    # Verifica se o arquivo existe
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    # Remove o arquivo
    dao_documents.delete_database_document(document_id)
    os.remove(file_path)

    return {'message': 'Document deleted!'}
