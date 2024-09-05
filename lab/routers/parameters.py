from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, HTTPException

from lab.models import Message, Parameter

from ..dao.dao_parameters import (
    add_database_parameter,
    delete_database_parameter,
    list_database_parameters,
    update_database_parameter,
)

router = APIRouter(tags=['Parameters'])


@router.post(
    '/parameter',
    response_model=Parameter,
    status_code=HTTPStatus.CREATED,
)
def create_parameter(parameter: str):
    parameter = add_database_parameter(parameter)
    return parameter


@router.get('/parameter', response_model=list[Parameter])
def list_parameters():
    parameters = list_database_parameters()
    if not parameters:
        raise HTTPException(status_code=404, detail='No parameters found')
    return parameters


@router.put('/parameter', response_model=Parameter)
def update_parameter(parameter: Parameter):
    parameter = update_database_parameter(parameter)
    return parameter


@router.delete('/parameter/{parameter_id}', response_model=Message)
def delete_parameter(parameter_id: UUID):
    delete_database_parameter(parameter_id)
    return {'message': 'Parameter deleted!'}
