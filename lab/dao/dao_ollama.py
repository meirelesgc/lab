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

    prompt = f"""
        # Instruções
        Remova do texto a seguir todas as datas que encontrar,
        subistitua por '---';

        Remova do texto a seguir todas os nomes proprios que encontrar,
        subistitua por '---';

        Não altere o restante do texto;

        '''
        {text}
        '''
        """

    model = Ollama(model='llama3.1', temperature=0.1)
    text = model.invoke(prompt)

    script_sql = """
        UPDATE documents
        SET document = %s
        WHERE document_id = %s;
        """

    with Connection() as conn:
        conn.exec(script_sql, [text, document_id])
