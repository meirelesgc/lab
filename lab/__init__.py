import os
from http import HTTPStatus
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from lab.models import Document, Message, Parameter
from lab.routers import openAI

from .dao.dao_documents import (
    add_database_document,
    delete_database_document,
    list_database_documents,
)
from .dao.dao_ollama import add_database_text
from .dao.dao_parameters import (
    add_database_parameter,
    delete_database_parameter,
    list_database_parameters,
    update_database_parameter,
)

load_dotenv()

app = FastAPI()
app.include_router(openAI.router)


@app.post('/file', status_code=HTTPStatus.CREATED, response_model=Document)
def upload_file(file: UploadFile = File(...)):
    # Registrar que foi salvo e gerar um identificador
    document = add_database_document(file.filename)

    # Salvar o arquivo localmente
    with open(f'documents/{document.document_id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())

    # Etapa dois do registro
    add_database_text(document.document_id)

    # Concluir a operação
    return document


@app.get('/file', response_model=list[Document])
def list_files():
    documents = list_database_documents()
    if not documents:
        raise HTTPException(status_code=404, detail='No parameters found')
    return documents


@app.get(
    '/file/{document_id}',
    response_class=FileResponse,
)
def get_file(document_id: UUID):
    file_path = f'documents/{document_id}.pdf'

    # Verifica se o arquivo existe
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    return FileResponse(file_path)


@app.delete(
    '/file/{document_id}',
    response_model=Message,
)
def delete_file(document_id: UUID):
    file_path = f'documents/{document_id}.pdf'

    # Verifica se o arquivo existe
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    # Remove o arquivo
    delete_database_document(document_id)
    os.remove(file_path)

    return {'message': 'Document deleted!'}


@app.post(
    '/parameter',
    response_model=Parameter,
    status_code=HTTPStatus.CREATED,
)
def create_parameter(parameter: str):
    parameter = add_database_parameter(parameter)
    return parameter


@app.get('/parameter', response_model=list[Parameter])
def list_parameters():
    parameters = list_database_parameters()
    if not parameters:
        raise HTTPException(status_code=404, detail='No parameters found')
    return parameters


@app.put('/parameter', response_model=Parameter)
def update_parameter(parameter: Parameter):
    parameter = update_database_parameter(parameter)
    return parameter


@app.delete('/parameter', response_model=Message)
def delete_parameter(parameter_id: UUID):
    delete_database_parameter(parameter_id)
    return {'message': 'Parameter deleted!'}
