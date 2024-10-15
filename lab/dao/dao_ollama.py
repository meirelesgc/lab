import json
import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.llms.ollama import Ollama
from unidecode import unidecode

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


def parse_metadata(string):
    string = string.splitlines(keepends=False)
    string = [line for line in string if '<|end-output|>' not in line]
    cleaned_string = '\n'.join(string).strip().replace("'", '"')
    try:
        metadata = json.loads(cleaned_string)
        return metadata['Metadata']
    except (json.JSONDecodeError, KeyError):
        return None


def add_database_metadata(document_id):
    text = document_to_text(document_id)
    prompt = f"""
        You are tasked with extracting specific information from the following text:

        ```
        <{text}>
        ```

        Please follow the steps below and fill in the table with the requested information:

        1. **Patient's Name**: Look for phrases like "Patient Name:", "The patient is", or any context that introduces the patient's name.
        2. **Patient's Identifier**: This could be a CPF, RG, or other identifying numbers. Look for labels such as "CPF:", "RG:", or similar.
        3. **Doctor's Name**: Search for phrases like "Doctor's Name:", "The doctor is", or any context that introduces the doctor's name.
        4. **Doctor's Identifier**: This could include CPF, RG, council number, CRM, or other identifiers. Look for labels such as "Doctor's CPF:", "Doctor's CRM:", or similar.
        5. **Date of Issuance**: Look for phrases like "Issued on:", "Date:", or any context that indicates the date of issuance.

        Please complete the table below with the extracted information:

        | **Field**               | **Extracted Information**   |
        |-------------------------|-----------------------------|
        | Patient's Name          | [Extracted Name]            |
        | Patient's Identifier    | [Extracted Identifier]      |
        | Doctor's Name           | [Extracted Name]            |
        | Doctor's Identifier     | [Extracted Identifier]      |
        | Date of Issuance        | [Extracted Date]            |
|
        Return only the completed table with the extracted data.
        """  # noqa: E501

    model = Ollama(model='gemma2', temperature=0.0)
    text = model.invoke(prompt)

    prompt = """
        ### Template:
        {
            'patient_name': "",
            'patient_identifier': "",
            'doctor_name': "",
            'doctor_identifier': "",
            'date_issuance': ""
        }

        ### Example:
        {
            'patient_name': "Ana Oliveira",
            'patient_identifier': "987.654.321-00",
            'doctor_name': "Dr. João Silva",
            'doctor_identifier': "12345",
            'date_issuance': "2024-10-11"
        }

        ### Text:
        """
    prompt += text
    model = Ollama(model='nuextract', temperature=0.0)
    text = model.invoke(prompt)

    metadata = parse_metadata(text)
    return metadata


def sanitize_text(text):
    text = unidecode(text)
    return ''.join(char for char in text if char.isalnum())


def add_database_text(document_id):
    text = document_to_text(document_id)

    prompt = f"""
        Você é um especialista em segurança da informação. Preciso que ajuste um texto para cumprir a LGPD, trocando os dados sensíveis sem alterar outras informações assim como esta especificado abaixo.

        Substitua os dados no texto conforme as seguintes instruções:

        - Datas: `<DATA>`
        - Nomes de pessoas: `<NOME>`
        - Nomes de instituições: `<NOME_ENTIDADE>`
        - Qualquer forma de identificar médicos: `<MEDICO>`
        - Códigos que identificam pessoas (CPF, RG, CRM): `<ID_PESSOA>`
        - **Mantenha os sintomas no texto original. Não os remova ou modifique.**

        Coloque o texto entre as tags `<CleanText>`, sem comentários adicionais.

        **Texto original a ser limpo:**

        ```
        {text}
        ```
        """  # noqa: E501

    model = Ollama(model='gemma2', temperature=0.0)
    text = model.invoke(prompt)

    SCRIPT_SQL = """
        UPDATE documents
        SET
            document = %(document)s,
            status = 'STANDBY'
        WHERE document_id = %(document_id)s;
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'document': text, 'document_id': document_id})
