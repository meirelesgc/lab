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
            documents;
        """
    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)

    documents = []
    if documents:
        for document_id, name, status, created_at in registry:
            documents.append(
                Document(
                    document_id=document_id,
                    name=name,
                    status=status,
                    created_at=created_at,
                )
            )
    return documents


def delete_database_document(document_id) -> None:
    SCRIPT_SQL = """
        DELETE FROM documents
        WHERE document_id = %(document_id)s;
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, str(document_id))
