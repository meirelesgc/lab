import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from langchain_community.callbacks.manager import get_openai_callback
from langchain.schema.document import Document
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import Field, create_model
from unidecode import unidecode

from .. import prompts
from ..config import settings
from ..dao import Connection, dao_parameters
from ..models import Parameter, EvaluateDocumentData, DocumentData

CHROMA_PATH = "chroma"


def load_documents(document_id: UUID):
    document_loader = PyPDFLoader(f"documents/{document_id}.pdf")
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
    embeddings = OllamaEmbeddings(model="mxbai-embed-large:latest")
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
        new_chunk_ids = [chunk.metadata["id"] for chunk in chunks]
        db.add_documents(chunks, ids=new_chunk_ids)


def index_chunks(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        chunk.metadata["id"] = chunk_id

    return chunks


def remove_from_chroma(document_id: UUID):
    db = get_chroma()

    existing_items = db.get(include=[])
    ids = [existing_id for existing_id in existing_items['ids'] if str(document_id) in existing_id]  # fmt: skip
    db.delete(ids=ids)


def get_date(document_id: UUID):
    model = OllamaLLM(model="nuextract")

    metadata = ['data', 'data registro', 'data atendimento', 'data exame', '1 de Janeiro de 2024', 'Jan 1, 2024', '01/01/2024', '2024/01/01']  # fmt: skip
    chunks = search_chunks(document_id, metadata)
    for _, chunk in enumerate(chunks.values()):
        prompt = create_context(
            chunk,
            schema=prompts.DATE_METADATA_SCHEMA,
            example=prompts.DATE_METADATA_EXAMPLE,
        )
        date = model.invoke(prompt)
        try:
            date = date.strip().split("<|end-output|>")
            date = json.loads(date[0])
            if date := date.get("date", None):
                date = datetime.strptime(date, "%d/%m/%Y")
                with Connection() as conn:
                    date = {"date": date, "document_id": document_id}
                    SCRIPT_SQL = """
                        UPDATE documents
                        SET document_date = %(date)s
                        WHERE document_id = %(document_id)s;
                        """
                    conn.exec(SCRIPT_SQL, date)
                    break
        except ValueError:
            print("Error parsing date")
        except json.JSONDecodeError:
            print("Error parsing JSON string:")


def get_patient(document_id: UUID):
    model = OllamaLLM(model="nuextract")

    metadata = ['nome', 'paciente', 'identificação', 'cliente', 'usuario', 'registro', 'indivíduo', 'pessoa', 'identidade', 'perfil', 'sujeito', 'nome_completo', 'dados_pessoais']  # fmt: skip
    chunks = search_chunks(document_id, metadata)

    for chunk in chunks.values():
        prompt = create_context(
            chunk,
            schema=prompts.PATIENT_METADATA_SCHEMA,
            example=prompts.PATIENT_METADATA_EXAMPLE,
        )
        user_data = model.invoke(prompt)
        try:
            user_data = user_data.strip().split("<|end-output|>")
            user_data = json.loads(user_data[0])
            if name := user_data.get("name", None):
                with Connection() as conn:
                    SCRIPT_SQL = """
                        SELECT patient_id
                        FROM patients
                        WHERE COALESCE(similarity(name, %(name)s), 0) + COALESCE(similarity(identifier, %(identifier)s), 0) > 0.4
                        ORDER BY COALESCE(similarity(name, %(name)s), 0) + COALESCE(similarity(identifier, %(identifier)s), 0) DESC
                        LIMIT 1;
                        """
                    patient = {"name": name, "identifier": str(user_data)}
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
                            "patient_id": registry[0].get("patient_id"),
                            "document_id": document_id,
                        },
                    )
        except json.JSONDecodeError:
            print("Error parsing JSON string:")


def search_chunks(document_id, parameter):
    db = get_chroma()
    source = {"source": f"documents/{document_id}.pdf"}

    chunks = {}
    chunk_score = {}
    chunk_recorency = {}

    vocabulary = parameter.synonyms + [parameter.parameter]
    for data in vocabulary:
        results = db.similarity_search_with_score(data, k=3, filter=source)

        for doc, score in results:
            doc_id = doc.metadata.get("id")
            if doc_id is None:
                continue

            if doc_id not in chunks:
                chunks[doc_id] = doc.page_content
                chunk_score[doc_id] = score
                chunk_recorency[doc_id] = 1
            else:
                chunk_score[doc_id] += score
                chunk_recorency[doc_id] += 1

    scores = {doc_id: chunk_score[doc_id] / chunk_recorency[doc_id] for doc_id in chunks}  # fmt: skip
    top_chunks = sorted(scores, key=scores.get, reverse=True)[:3]

    return {doc_id: chunks[doc_id] for doc_id in top_chunks}


def clear_text(document_id):
    db = get_chroma()
    model = OllamaLLM(model="gemma2")

    source = {"source": f"documents/{document_id}.pdf"}
    result = db.get(where=source)

    content = list()
    result = zip(result["ids"], result["documents"], result["metadatas"])
    for doc_id, page_content, metadata in result:
        prompt = prompts.CLEAR_TEXT_PROMPT.format(content=page_content)
        clean_content = model.invoke(prompt)
        content.append(clean_content)
        new_doc = Document(page_content=clean_content, metadata=metadata)
        db.update_document(document_id=doc_id, document=new_doc)

    with Connection() as conn:
        SCRIPT_SQL = """
            UPDATE documents SET
            status = 'STANDBY',
            document = %(text)s
            WHERE document_id = %(document_id)s;
            """
        conn.exec(
            SCRIPT_SQL,
            {"document_id": document_id, "text": "\n\n---\n\n".join(content)},
        )


def create_context(text, schema, example=["", "", ""]):
    prompt = f"<|input|>\n### Template:\n{json.dumps(json.loads(schema), indent=4)}\n"
    prompt += ''.join(f'### Example:\n{json.dumps(json.loads(i), indent=4)}\n' for i in example if i)  # fmt: skip
    return prompt + f"### Text:\n{text}\n<|output|>\n"


def dynamic_class(parameters: List[Parameter]):
    dynamic_fields = {}
    for param in parameters:
        field_name = unidecode(param.parameter.strip().lower().replace(" ", "_"))
        field_name = param.parameter
        dynamic_fields[field_name] = (
            Optional[str],
            Field(None, description=", ".join(param.synonyms)),
        )
    return create_model("Data", **dynamic_fields)


def get_chunks_from_parameters(document_id, parameters):
    chunk_reference = {}
    chunks = {}
    for parameter in parameters:
        result = search_chunks(document_id, parameter)
        for chunk_id, content in result.items():
            if chunk_id not in chunk_reference:
                chunk_reference[chunk_id] = []
            chunk_reference[chunk_id].append(parameter)
        chunks.update(result)
    return chunk_reference, chunks


def generate_aggregated_prompt(chunk_reference, chunks, model):
    aggregated_prompt = ""
    for key, value in chunk_reference.items():
        parser = PydanticOutputParser(pydantic_object=dynamic_class(value))
        prompt_template = PromptTemplate.from_template(template=prompts.TEMPLATE)
        prompt = prompt_template.format(
            format_instructions=parser.get_format_instructions(),
            context=chunks[key],
        )
        aggregated_prompt += f"{prompt}\n\n---\n\n"
    return aggregated_prompt


def process_chunk_data(chunk_reference, chunks, model):
    aggregated_data = {}
    price = 0

    for key, value in chunk_reference.items():
        parser = PydanticOutputParser(pydantic_object=dynamic_class(value))
        prompt_template = PromptTemplate.from_template(template=prompts.TEMPLATE)
        prompt = prompt_template.format(
            format_instructions=parser.get_format_instructions(),
            context=chunks[key],
        )
        with get_openai_callback() as callback:
            response = model.invoke(prompt)
        price += callback.total_cost
        data = parser.invoke(response)

        for field_name, field_value in data.model_dump().items():
            if field_value not in [None, ""]:
                if field_name not in aggregated_data:
                    aggregated_data[field_name] = []
                aggregated_data[field_name].append(field_value)

    return aggregated_data, price


def insert_data_to_db(document_id, aggregated_prompt, aggregated_data, price):
    with Connection() as conn:
        SCRIPT_SQL = """
            INSERT INTO document_data (document_id,
                                         prompt,
                                         document_data,
                                         price)
            VALUES (%(document_id)s,
                    %(prompt)s,
                    %(document_data)s,
                    %(price)s);
        """
        insert_data = {
            "document_id": document_id,
            "prompt": aggregated_prompt,
            "document_data": json.dumps(aggregated_data),
            "price": price,
        }
        conn.exec(SCRIPT_SQL, insert_data)


def extract_data(document_id):
    model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, temperature=0.0, seed=1)
    parameters = dao_parameters.list_database_parameters()

    chunk_reference, chunks = get_chunks_from_parameters(document_id, parameters)
    aggregated_prompt = generate_aggregated_prompt(chunk_reference, chunks, model)
    document_data, price = process_chunk_data(chunk_reference, chunks, model)

    insert_data_to_db(document_id, aggregated_prompt, document_data, price)

    return DocumentData(**{"document_id": document_id, "document_data": document_data})


def evaluate_data(document_data: EvaluateDocumentData):
    with Connection() as conn:
        SCRIPT_SQL = """
            UPDATE document_data
            SET rating = %(rating)s,
                evaluated_document_data = %(evaluated_document_data)s,
                updated_at = CURRENT_TIMESTAMP
            WHERE document_id = %(document_id)s;
        """

        document_data = document_data.model_dump()
        document_data["document_data"] = (json.dumps(document_data["document_data"]),)
        conn.exec(SCRIPT_SQL, document_data)

        SCRIPT_SQL = """
            UPDATE documents
            SET status = 'DONE'
            WHERE document_id = %(document_id)s;
        """

        conn.exec(SCRIPT_SQL, {"document_id": document_data.document_id})
