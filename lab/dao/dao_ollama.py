import json
from datetime import datetime
from uuid import UUID

from langchain.schema.document import Document
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..dao import Connection
from ..prompts import (
    CLEAR_TEXT_PROMPT,
    DATE_METADATA_EXAMPLE,
    DATE_METADATA_SCHEMA,
    PATIENT_METADATA_EXAMPLE,
    PATIENT_METADATA_SCHEMA,
)

CHROMA_PATH = 'chroma'


def load_documents(document_id: UUID):
    document_loader = PyPDFLoader(f'documents/{document_id}.pdf')
    return document_loader.load()


def split_documents(document: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(document)


def get_embedding_function():
    embeddings = OllamaEmbeddings(model='all-minilm:33m')
    return embeddings


def get_chroma():
    return Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function(),
    )


def embed_document(document_id):
    document = load_documents(document_id)
    chunks = split_documents(document)
    add_to_chroma(chunks)


def add_to_chroma(chunks: list[Document]):
    new_chunk_ids = list()

    db = get_chroma()
    chunks = index_chunks(chunks)
    if len(chunks):
        new_chunk_ids = [chunk.metadata['id'] for chunk in chunks]
        db.add_documents(chunks, ids=new_chunk_ids)


def index_chunks(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get('source')
        page = chunk.metadata.get('page')
        current_page_id = f'{source}:{page}'

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f'{current_page_id}:{current_chunk_index}'
        last_page_id = current_page_id

        chunk.metadata['id'] = chunk_id

    return chunks


def remove_from_chroma(document_id: UUID):
    db = get_chroma()

    existing_items = db.get(include=[])
    ids = [existing_id for existing_id in existing_items['ids'] if str(document_id) in existing_id]  # fmt: skip
    db.delete(ids=ids)


def get_date(document_id: UUID):
    model = OllamaLLM(model='nuextract')

    metadata = ['data', 'data registro', 'data atendimento', 'data exame', '1 de Janeiro de 2024', 'Jan 1, 2024', '01/01/2024', '2024/01/01']  # fmt: skip
    chunks = search_chunks(document_id, metadata)
    for _, chunk in enumerate(chunks.values()):
        prompt = create_context(
            chunk,
            schema=DATE_METADATA_SCHEMA,
            example=DATE_METADATA_EXAMPLE,
        )
        date = model.invoke(prompt)
        try:
            date = date.strip().split('<|end-output|>')
            date = json.loads(date[0])
            if date := date.get('date', None):
                print(date)
                date = datetime.strptime(date, '%d/%m/%Y')
                with Connection() as conn:
                    date = {'date': date, 'document_id': document_id}
                    SCRIPT_SQL = """
                        UPDATE documents
                        SET document_date = %(date)s
                        WHERE document_id = %(document_id)s;
                        """
                    conn.exec(SCRIPT_SQL, date)
                    print('Cheguei até aqui')
                    break
        except json.JSONDecodeError:
            print('Error parsing JSON string:')


def get_patient(document_id: UUID):
    model = OllamaLLM(model='nuextract')

    metadata = ['nome', 'paciente', 'identificação', 'cliente', 'usuario', 'registro', 'indivíduo', 'pessoa', 'identidade', 'perfil', 'sujeito', 'nome_completo', 'dados_pessoais']  # fmt: skip
    chunks = search_chunks(document_id, metadata)

    for _, chunk in enumerate(chunks.values()):
        prompt = create_context(
            chunk,
            schema=PATIENT_METADATA_SCHEMA,
            example=PATIENT_METADATA_EXAMPLE,
        )
        user_data = model.invoke(prompt)
        try:
            user_data = user_data.strip().split('<|end-output|>')
            user_data = json.loads(user_data[0])
            if name := user_data.get('name', None):
                with Connection() as conn:
                    SCRIPT_SQL = """
                        SELECT patient_id
                        FROM patients
                        WHERE COALESCE(similarity(name, %(name)s), 0) + COALESCE(similarity(identifier, %(identifier)s), 0) > 0.4
                        ORDER BY COALESCE(similarity(name, %(name)s), 0) + COALESCE(similarity(identifier, %(identifier)s), 0) DESC
                        LIMIT 1;
                        """
                    patient = {'name': name, 'identifier': str(user_data)}
                    registry = conn.select(SCRIPT_SQL, patient)
                    if not registry:
                        SCRIPT_SQL = """
                            INSERT INTO patients (name, identifier)
                            VALUES (%(name)s, %(identifier)s)
                            RETURNING patient_id;
                            """
                        registry = [conn.exec_with_result(SCRIPT_SQL, patient)]
                    SCRIPT_SQL = """
                        UPDATE documents
                        SET unverified_patient = unverified_patient || %(patient_id)s
                        WHERE document_id = %(document_id)s;
                        """
                    conn.exec(
                        SCRIPT_SQL,
                        {
                            'patient_id': registry[0].get('patient_id'),
                            'document_id': document_id,
                        },
                    )
        except json.JSONDecodeError:
            print('Error parsing JSON string:')


def search_chunks(document_id, vocabulary):
    db = get_chroma()

    chunks = {}
    for data in vocabulary:
        source = {'source': f'documents/{document_id}.pdf'}
        results = db.similarity_search_with_score(data, k=1, filter=source)

        for doc, _score in results:
            doc_id = doc.metadata.get('id', None)
            if doc_id not in chunks:
                chunks[doc_id] = doc.page_content
    return chunks


def clear_text(document_id):
    db = get_chroma()
    model = OllamaLLM(model='gemma2')

    source = {'source': f'documents/{document_id}.pdf'}
    result = db.get(where=source)

    result = zip(result['ids'], result['documents'], result['metadatas'])
    for doc_id, page_content, metadata in result:
        prompt = CLEAR_TEXT_PROMPT.format(content=page_content)
        clean_content = model.invoke(prompt)
        new_doc = Document(page_content=clean_content, metadata=metadata)
        db.update_document(document_id=doc_id, document=new_doc)

    with Connection() as conn:
        SCRIPT_SQL = """
            UPDATE documents SET
            status = 'STANDBY'
            WHERE document_id = %(document_id)s;
            """
        conn.exec(SCRIPT_SQL, {'document_id': document_id})


def create_context(text, schema, example=['', '', '']):
    prompt = f'<|input|>\n### Template:\n{json.dumps(json.loads(schema), indent=4)}\n'
    prompt += ''.join(f'### Example:\n{json.dumps(json.loads(i), indent=4)}\n' for i in example if i)  # fmt: skip
    return prompt + f'### Text:\n{text}\n<|output|>\n'
