import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms.ollama import Ollama

from ..dao import Connection


def document_to_text(document_id):
    filename = f'{document_id}.pdf'
    file_path = os.path.join('documents', filename)

    document_loader = PyPDFLoader(file_path)
    documents = document_loader.load()

    text = list()
    for document in documents:
        text.append(document.page_content.replace('\n', ' '))

    text = str(' ').join(text)
    return text


def add_database_text(document_id):
    text = document_to_text(document_id)

    print(text)
    prompt = f"""
        Você é um especialista em segurança da informação.

        Quero sua ajuda para reescrever um texto, removendo informações específicas. O objetivo é assegurar que cumpriremos a LGPD, eliminando os dados sensíveis que não devem ser trafegados.

        É crucial que o texto reescrito **não tenha os dados alterados além do que for pedido**. Por favor, substitua as informações no texto por tags específicas:

        - Datas: `<DATA>`
        - Nomes de pessoas: `<NOME>`
        - Nomes de instituições: `<NOME_ENTIDADE>`
        - Qualquer forma de identificar os médicos: `<MEDICO>`
        - Códigos que identificam pessoas (CPF, RG, CRM): `<ID_PESSOA>`
        - Sintomas: mantenha os sintomas no texto original.

        Coloque o texto resultante entre as tags `<CleanText>`.

        ```
        {text}
        ```
        """  # noqa: E501

    model = Ollama(model='llama3.2', temperature=0.1)
    text = model.invoke(prompt)
    print(text)
    SCRIPT_SQL = """
        UPDATE documents
        SET
            document = %(document)s,
            status = 'STANDBY'
        WHERE document_id = %(document_id)s;
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'document': text, 'document_id': document_id})
