import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms.ollama import Ollama

from ..dao import Connection


def document_to_text(file_path):
    document_loader = PyPDFLoader(file_path)
    documents = document_loader.load()

    text = list()
    for document in documents:
        text.append(document.page_content.replace('\n', ' '))

    text = str(' ').join(text)
    return text


def cleam_text(document_id):
    filename = f'{document_id}.pdf'
    file_path = os.path.join('documents/exams', filename)

    text = document_to_text(file_path)
    prompt = f"""
        Instruções: remova do texto a seguir todas as datas que encontrar,
        subistitua por '---', não altere o restante do texto;

        '''
        {text}
        '''
        """
    model = Ollama(model='llama3.1:8b', temperature=0.1)
    text = model.invoke(prompt)

    script_sql = """
        UPDATE documents
        SET document = %s
        WHERE document_id = %s;
        """

    with Connection() as conn:
        conn.exec(script_sql, [text, document_id])
