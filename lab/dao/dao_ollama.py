import json
import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaLLM
from unidecode import unidecode

from ..dao import Connection


def document_to_text(document_id):
    filename = f'{document_id}.pdf'
    file_path = os.path.join('documents', filename)

    document_loader = PyPDFLoader(file_path)
    documents = document_loader.load()

    text = list()
    for document in documents:
        text.append(document.page_content)

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

    model = OllamaLLM(model='gemma2', temperature=0.0)
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
    model = OllamaLLM(model='nuextract', temperature=0.0)
    text = model.invoke(prompt)

    metadata = parse_metadata(text)
    print(metadata)
    return metadata


def sanitize_text(text):
    text = unidecode(text)
    return ''.join(char for char in text if char.isalnum())


def add_database_text(document_id):
    filename = f'{document_id}.pdf'
    file_path = os.path.join('documents', filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f'Arquivo {file_path} não encontrado.')

    document_loader = PyPDFLoader(file_path)
    documents = document_loader.load()

    prompts = {
        '<DATA>': 'Remova qualquer data e substitua pelo token <DATA>.',
        '<NOME>': 'Remova qualquer nome de pessoa e substitua pelo token <NOME>.',
        '<NOME_ENTIDADE>': 'Remova qualquer nome de instituição e substitua pelo token <NOME_ENTIDADE>.',
        '<MEDICO>': 'Remova qualquer nome ou identificação de médicos e substitua pelo token <MEDICO>.',
        '<ID_PESSOA>': 'Remova qualquer código de identificação de pessoas (CPF, RG, CRM) e substitua pelo token <ID_PESSOA>.',
    }

    for document in documents:
        for tag, prompt_instruction in prompts.items():
            prompt = f"""
                {document}

                Utilize o texto anterior como referência. Não altere o formato ou conteúdo além do que for pedido.

                {prompt_instruction}

                **Exemplos:**

                Antes: O paciente João da Silva, 35 anos, compareceu ao Hospital São Lucas no dia 12/03/2023 com queixas de dor abdominal.
                Depois: O paciente <NOME>, 35 anos, compareceu ao <NOME_ENTIDADE> no dia <DATA> com queixas de dor abdominal.

                **Observações:**

                * **Se não encontrar elementos a serem substituídos, não faça nenhuma alteração.**
                * **Mantenha os sintomas no texto original.**
                * **Priorize a preservação da coesão e da legibilidade do texto.**
                """

            document.page_content = OllamaLLM(model='gemma2').invoke(prompt)

    text = '\n'.join([document.page_content for document in documents])

    SCRIPT_SQL = """
        UPDATE documents
        SET
            document = %(document)s,
            status = 'STANDBY'
        WHERE document_id = %(document_id)s;
        """

    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'document': text, 'document_id': document_id})
