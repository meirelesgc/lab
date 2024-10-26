from ..dao import Connection
from ..models import Document


def add_database_document(filename: str) -> Document:
    document = Document(name=filename)

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


def list_database_documents() -> list[Document]:
    SCRIPT_SQL = """
        SELECT
            document_id,
            name,
            status,
            created_at
        FROM
            documents
        ORDER BY
            status,
            created_at 	DESC;
        """
    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)

    documents = []
    if registry:
        documents = [Document(**document) for document in registry]
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
