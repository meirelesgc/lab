import os
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from lab.models import Document, DocumentMetadata, Message

# from ..celery import celery
from ..dao import dao_documents, dao_ollama

router = APIRouter(tags=['Documents'])


@router.post(
    '/file', status_code=HTTPStatus.CREATED, response_model=list[Document]
)
def upload_files(
    files: list[UploadFile] = File(...),
    metadata: DocumentMetadata | None = Header(None),
):
    documents = []

    for file in files:
        document = dao_documents.add_database_document(file.filename)

        with open(f'documents/{document.document_id}.pdf', 'wb') as buffer:
            buffer.write(file.file.read())

        dao_ollama.embed_document(document.document_id)
        # dao_ollama.get_patient(document.document_id)
        dao_ollama.get_date(document.document_id)

        documents.append(document)
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

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    return FileResponse(file_path)


@router.delete(
    '/file/{document_id}',
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
