import os

import spacy
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms.ollama import Ollama

from ..dao import Connection

nlp = spacy.load('pt_core_news_lg')


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

    # text = remove_named_entities(text)

    # prompt = f"""
    #     ### Instruções

    #     1. **Remova todas as datas** que encontrar no texto a seguir e substitua por `'---'`.
    #     2. **Remova todos os nomes próprios e entidades nomeadas** que encontrar no texto a seguir e substitua por `'---'`.
    #     3. **Não altere o restante do texto.**

    #     ```

    #     {text}

    #     """  # noqa: E501

    # model = Ollama(model='llama3.1', temperature=0.1)
    # text = model.invoke(prompt)

    SCRIPT_SQL = """
        UPDATE documents
        SET
            document = %(document)s,
            status = 'STANDBY'
        WHERE document_id = %(document_id)s;
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'document': text, 'document_id': document_id})


def remove_named_entities(text):
    doc = nlp(text)
    text = [token.text for token in doc if not token.ent_type_]
    cleaned_text = ' '.join(text)
    return cleaned_text
