from http import HTTPStatus
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from lab.security import (
    create_access_token,
    credentials_exception,
    get_current_user,
    verify_password,
)

from ..dao import dao_users
from ..models import Message, Token, UserPublic, UserSchema

router = APIRouter(tags=['Admin'])


@router.post(
    '/user/', status_code=HTTPStatus.CREATED, response_model=UserPublic
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
    '/user/', status_code=HTTPStatus.OK, response_model=list[UserPublic]
)
def list_users():
    users = dao_users.list_users()
    return users


@router.put(
    '/user/{user_id}',
    status_code=HTTPStatus.OK,
    response_model=UserPublic,
)
def update_user(
    user_id: UUID,
    user: UserSchema,
    current_user: str = Depends(get_current_user),
):
    current_user = dao_users.user_email_exists(current_user)
    if not current_user:
        raise credentials_exception

    if current_user['user_id'] != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions'
        )

    if not dao_users.user_id_exists(user_id):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not Found',
        )
    user = dao_users.update_user(user_id, user)
    return user


@router.delete('/user/{user_id}', response_model=Message)
def delete_user(
    user_id: UUID,
    current_user: str = Depends(get_current_user),
):
    current_user = dao_users.user_email_exists(current_user)
    if not current_user:
        raise credentials_exception

    if current_user['user_id'] != user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions'
        )

    dao_users.delete_user(user_id)
    return {'message': 'User deleted'}


@router.post('/token', response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = dao_users.user_email_exists(email=form_data.username)

    if user and verify_password(form_data.password, user['password']):
        access_token = create_access_token(data={'sub': user['email']})
        return {'access_token': access_token, 'token_type': 'baerer'}

    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail='Incorrect email or password',
    )
