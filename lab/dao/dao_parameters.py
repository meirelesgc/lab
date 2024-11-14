from uuid import UUID

from ..dao import Connection
from ..models import BaseParameter, Parameter


def add_database_parameter(parameter: BaseParameter) -> Parameter:
    parameter = Parameter(**parameter.model_dump())

    SCRIPT_SQL = """
        INSERT INTO public.parameters(parameter_id,
                                      parameter,
                                      synonyms)
        VALUES (%(parameter_id)s, %(parameter)s, %(synonyms)s);
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, parameter.model_dump())

    return parameter


def update_database_parameter(parameter: Parameter):
    SCRIPT_SQL = """
        UPDATE parameters SET
            parameter = %(parameter)s,
            synonyms = %(synonyms)s
        WHERE parameter_id = %(parameter_id)s
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, parameter.model_dump())

    return parameter


def delete_database_parameter(parameter_id: UUID):
    SCRIPT_SQL = """
        DELETE FROM parameters
        WHERE parameter_id = %(parameter_id)s
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'parameter_id': parameter_id})


def list_database_parameters():
    SCRIPT_SQL = """
        SELECT parameter_id, parameter, synonyms
        FROM parameters;
        """
    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)
    parameters = []
    if registry:
        parameters = [Parameter(**parameter) for parameter in registry]
    return parameters
