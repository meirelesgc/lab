import json
from uuid import UUID

from ..dao import Connection
from ..models import BaseDocument, Document, EvaluateDocumentData


def add_database_document(filename: str) -> BaseDocument:
    document = BaseDocument(name=filename)

    SCRIPT_SQL = """
        INSERT INTO public.documents (document_id,
                                      name,
                                      status,
                                      created_at)
        VALUES (%(document_id)s,
                %(name)s,
                %(status)s,
                %(created_at)s);
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, document.model_dump())
    return document


def list_database_documents() -> list[BaseDocument]:
    SCRIPT_SQL = """
        SELECT
            doc.document_id,
            doc.name,
            doc.status,
            doc.created_at
        FROM
            documents doc
        ORDER BY
            doc.status,
            doc.created_at DESC;
        """

    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)

    documents = []
    if registry:
        documents = [BaseDocument(**document) for document in registry]
    return documents


def delete_database_document(document_id) -> None:
    SCRIPT_SQL = """
        DELETE FROM documents
        WHERE document_id = %(document_id)s;
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'document_id': document_id})


def select_llm_documents(document_id=None):
    SCRIPT_SQL = """
        SELECT document_id, document
        FROM documents
        WHERE status = 'STANDBY' OR status = 'DONE'
        """

    if document_id is not None:
        SCRIPT_SQL += 'AND document_id = %(document_id)s'

    with Connection() as conn:
        registry = conn.select(
            SCRIPT_SQL,
            {'document_id': document_id} if document_id is not None else {},
        )

    return registry or []


def get_document(document_id: UUID) -> Document:
    SCRIPT_SQL = """
        SELECT
            doc.document_id,
            doc.name,
            doc.status,
            doc.created_at,
            doc.document_date,
            COALESCE(
                jsonb_agg(jsonb_build_object(
                    'patient_id', pp.patient_id,
                    'name', pp.name
                )) FILTER (WHERE pp.patient_id IS NOT NULL),
                '[]'::jsonb
            ) AS patients,
            COALESCE(
                jsonb_agg(jsonb_build_object(
                    'patient_id', p.patient_id,
                    'name', p.name
                )) FILTER (WHERE p.patient_id IS NOT NULL),
                '[]'::jsonb
            ) AS unverified_patient
        FROM documents doc
        LEFT JOIN patients p ON p.patient_id = ANY(doc.unverified_patient)
        LEFT JOIN patients pp ON doc.patient_id = pp.patient_id
        WHERE
            doc.document_id = %(document_id)s
        GROUP BY
            doc.document_id
        ORDER BY
            doc.status,
            doc.created_at DESC;
        """
    with Connection() as conn:
        result = conn.select(SCRIPT_SQL, {'document_id': document_id})
    document = Document(**result[0])

    SCRIPT_SQL = """
        SELECT DISTINCT ON (document_id)
            data_id,
            document_data,
            rating,
            price,
            evaluated_document_data
        FROM public.document_data
        WHERE document_id = %(document_id)s
        ORDER BY document_id, created_at DESC;
        """

    with Connection() as conn:
        result = conn.select(SCRIPT_SQL, {'document_id': document_id})

    if result:
        document.document_data = result[0]
    return document


def update_data(evaluated_data: EvaluateDocumentData):
    with Connection() as conn:
        SCRIPT_SQL = """
            UPDATE document_data
                SET evaluated_document_data = %(document_data)s,
                    rating = %(rating)s
            WHERE data_id = %(data_id)s;
            """
        evaluated_data = evaluated_data.model_dump()

        evaluated_data['document_data'] = json.dumps(
            evaluated_data['document_data']
        )

        conn.exec(SCRIPT_SQL, evaluated_data)

        SCRIPT_SQL = """
            UPDATE documents
                SET patient_id = %(patient_id)s,
                    document_date = %(document_date)s
            WHERE document_id = %(document_id)s;
            """
        conn.exec(SCRIPT_SQL, evaluated_data)
