import json
import time
from decimal import Decimal

from openai import OpenAI

from ..dao import Connection
from ..models import JsonDocument, JsonDocumentEvaluation, JsonDocumentResponse


def parameters_list():
    SCRIPT_SQL = """
    SELECT ARRAY_AGG(parameter) FROM parameters
    """

    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)

    return registry[0][0]


def fetch_document(documents) -> list[JsonDocument]:
    parameters = '\n'.join(parameters_list())

    json_documents = []
    for document_id, document in documents:
        json_document = JsonDocument(document_id=document_id)

        start_time = time.time()
        prompt = create_prompt(parameters, document)
        document_json, price = structure_document(prompt)
        end_time = time.time()
        processing_time = end_time - start_time

        SCRIPT_SQL = """
            INSERT INTO documents_openai (json_id,
                                          document_id,
                                          document_json,
                                          price,
                                          processing_time)
            VALUES (%(json_id)s,
                    %(document_id)s,
                    %(document_json)s,
                    %(price)s,
                    %(processing_time)s)
            RETURNING document_json;
            """

        with Connection() as conn:
            registry = conn.exec_with_result(
                SCRIPT_SQL,
                {
                    'json_id': json_document.json_id,
                    'document_id': document_id,
                    'document_json': document_json,
                    'price': price,
                    'processing_time': processing_time,
                },
            )
            json_document.document_json = registry[0]
        json_documents.append(json_document)
    return json_documents


def create_prompt(parameters, document):
    prompt = f"""
        ## Instrução
        Dado esse texto, que contém informações sobre laudos clinicos de uma pessoa. Seu papel é extrair os RESULTADOS das seguintes substâncias presentes nesse laudo clinico no formato JSON:

            {parameters}

        # Aqui está o texto referente ao laudo clinico:

            {document}

        Sempre retorne um JSON que possuam chaves referentes a cada item que deve ser extraído, caso não encontre alguma informação solicitada retorne a chave com o valor Null
        """  # noqa: E501
    return prompt


def structure_document(prompt):
    MODEL = 'gpt-4-turbo'

    client = OpenAI()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                'role': 'system',
                'content': (
                    "You're a helpful assistant that extracts and "
                    'structure information in JSON from unstructured '
                    'text'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        temperature=0,
        top_p=0,
        response_format={'type': 'json_object'},
        seed=1,
    )

    price = price_per_document(
        completion.usage.prompt_tokens,
        completion.usage.completion_tokens,
    )
    document_json = completion.choices[0].message.content

    return document_json, price


def price_per_document(imput_tokens, output_tokens):
    IMPUT_PRICE = 0.000150
    OUTPUT_PRICE = 0.000600

    imput_price = Decimal(imput_tokens / 1000 * IMPUT_PRICE)
    output_price = Decimal(output_tokens / 1000 * OUTPUT_PRICE)

    price = imput_price + output_price

    return price


def select_dopenai_json() -> list[JsonDocumentResponse]:
    SCRIPT_SQL = """
        SELECT
            dopen.json_id,
            dopen.document_id,
            dopen.document_json,
            dopen.rating,
            dopen.evaluated_document_json,
            dopen.created_at
        FROM
            public.documents_openai dopen
            INNER JOIN (
                SELECT
                    document_id,
                    MAX(created_at) AS latest_created_at
                FROM
                    public.documents_openai
                GROUP BY
                    document_id) AS subquery
            ON dopen.document_id = subquery.document_id
            AND dopen.created_at = subquery.latest_created_at;
        """

    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)
    json_documents = []
    if registry:
        for (
            json_id,
            document_id,
            document_json,
            rating,
            evaluated_document_json,
            created_at,
        ) in registry:
            json_documents.append(
                JsonDocumentResponse(
                    json_id=json_id,
                    document_id=document_id,
                    document_json=document_json,
                    rating=rating,
                    evaluated_document_json=evaluated_document_json or {},
                    created_at=created_at,
                )
            )

    return json_documents


def select_single_dopenai_json(document_id) -> JsonDocumentResponse:
    SCRIPT_SQL = """
        SELECT
            dopen.json_id,
            dopen.document_id,
            dopen.document_json,
            dopen.rating,
            dopen.evaluated_document_json,
            dopen.created_at
        FROM
            public.documents_openai dopen
            INNER JOIN (
                SELECT
                    document_id,
                    MAX(created_at) AS latest_created_at
                FROM
                    public.documents_openai
                GROUP BY
                    document_id) AS subquery
            ON dopen.document_id = subquery.document_id
            AND dopen.created_at = subquery.latest_created_at
        WHERE
            dopen.document_id = %(document_id)s;
        """

    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL, {'document_id': document_id})

    json_documents = []
    if registry:
        for (
            json_id,
            document_id,  # noqa: PLR1704
            document_json,
            rating,
            evaluated_document_json,
            created_at,
        ) in registry:
            json_documents.append(
                JsonDocumentResponse(
                    json_id=json_id,
                    document_id=document_id,
                    document_json=document_json,
                    rating=rating,
                    evaluated_document_json=evaluated_document_json or {},
                    created_at=created_at,
                )
            )

    return json_documents[0]


def update_openai_json_documents(
    JsonDocumentEvaluation: JsonDocumentEvaluation,
):
    SCRIPT_SQL = """
        UPDATE documents_openai SET
            rating = %(rating)s,
            evaluated_document_json = %(evaluated_document_json)s
        WHERE json_id = %(json_id)s;
        """
    document_evaluation = JsonDocumentEvaluation.model_dump()
    document_evaluation['evaluated_document_json'] = json.dumps(
        document_evaluation['evaluated_document_json']
    )

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, document_evaluation)

    SCRIPT_SQL = """
        UPDATE documents SET
            status = 'DONE'
        WHERE document_id = %(document_id)s
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, document_evaluation)
