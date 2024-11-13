from uuid import UUID

from ..models import UserPublic, UserSchema
from . import Connection


def create_user(user: UserSchema) -> UserPublic:
    SCRIPT_SQL = """
        INSERT INTO users (username, password, email)
        VALUES (%(username)s, %(password)s, %(email)s)
        RETURNING user_id;
        """
    with Connection() as conn:
        result = conn.exec_with_result(SCRIPT_SQL, user.model_dump())
    return UserPublic(user_id=result['user_id'], **user.model_dump())


def list_users() -> UserPublic:
    SCRIPQ_SQL = """
        SELECT user_id, username, email
        FROM users;
        """
    with Connection() as conn:
        result = conn.select(SCRIPQ_SQL)
    return result


def update_user(user_id: UUID, user: UserSchema):
    SCRIPT_SQL = """
        UPDATE users SET
            username = %(username)s,
            email = %(email)s,
            password = %(password)s
        WHERE user_id = %(user_id)s;
        """
    user = {**user.model_dump(), 'user_id': user_id}
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, user)
    return user


def delete_user(user_id: UUID):
    SCRIPT_SQL = """
        DELETE FROM users
        WHERE user_id = %(user_id)s
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'user_id': user_id})
