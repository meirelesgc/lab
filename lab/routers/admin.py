from http import HTTPStatus
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException

from ..dao import dao_users
from ..models import Message, UserPublic, UserSchema

router = APIRouter(tags=['Admin'])


@router.post(
    '/user/',
    status_code=HTTPStatus.CREATED,
    response_model=UserPublic,
)
def create_user(user: UserSchema):
    try:
        user = dao_users.create_user(user)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail='User already exists.'
        )
    return user


@router.get(
    '/user/',
    status_code=HTTPStatus.OK,
    response_model=list[UserPublic],
)
def list_users():
    users = dao_users.list_users()
    return users


@router.put(
    '/user/',
    status_code=HTTPStatus.OK,
)
def update_user(user_id: UUID, user: UserSchema):
    user = dao_users.update_user(user_id, user)
    return user


@router.delete(
    '/user/{user_id}',
    response_model=Message,
)
def delete_user(user_id: UUID):
    dao_users.delete_user(user_id)
    return {'message': 'User deleted'}
