import time
from decimal import Decimal

from openai import OpenAI

from ..dao import Connection


def parameters_list():
    SCRIPT_SQL = """
    SELECT ARRAY_AGG(parameter) FROM parameters
    """

    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)

    return registry[0][0]


def fetch_document(documents):
    parameters = ' '.join(parameters_list())

    for document_id, document in documents:
        start_time = time.time()
        prompt = create_prompt(parameters, document)
        end_time = time.time()
        processing_time = end_time - start_time

        document_json, price = structure_document(prompt)

        SCRIPT_SQL = """
            INSERT INTO documents_openai (document_id,
                                          document_json,
                                          price,
                                          processing_time)
            VALUES (%(document_id)s,
                    %(document_json)s,
                    %(price)s,
                    %(processing_time)s)
            """
        with Connection() as conn:
            conn.exec(
                SCRIPT_SQL,
                {
                    'document_id': document_id,
                    'document_json': document_json,
                    'price': price,
                    'processing_time': processing_time,
                },
            )


def create_prompt(parameters, document):
    prompt = f"""
        ## Instrução

        Você receberá um texto contendo informações sobre laudos clínicos de um paciente. Sua tarefa é extrair os RESULTADOS das seguintes substâncias presentes no laudo clínico e retornar essas informações no formato JSON conforme abaixo:

            {parameters}

        Aqui está o texto do laudo clínico:

            {document}

        Por favor, sempre retorne um JSON com chaves para cada item solicitado. Se alguma informação não for encontrada, inclua a chave correspondente com o valor `null`.
        """  # noqa: E501
    return prompt


def structure_document(prompt):
    MODEL = 'gpt-4o-mini'

    client = OpenAI()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                'role': 'system',
                'content': "You're a helpful assistant that extracts and structure information in JSON from unstructured text",
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
