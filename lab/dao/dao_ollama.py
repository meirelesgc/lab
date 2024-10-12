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
        **Prompt:**

        You are tasked with extracting specific information from the following text:

        ```
        <{text}>
        ```

        Please follow these steps:

        1. **Identify the patient's name**: Look for phrases like "Patient Name:", "The patient is", or any context that introduces the patient’s name.
        2. **Identify the patient's identifier**: This could be a CPF, RG, or other identifying numbers. Look for labels such as "CPF:", "RG:", or similar.
        3. **Identify the doctor's name**: Search for phrases like "Doctor Name:", "The doctor is", or context that introduces the doctor's name.
        4. **Identify the doctor's identifier**: This could include CPF, RG, council number, CRM, or other identifiers. Look for labels such as "Doctor's CPF:", "Doctor's CRM:", or similar.
        5. **Identify the date of issuance**: Look for phrases like "Issued on:", "Date:", or any context that indicates the date of issuance.

        Please return **only** the following data in a structured format, without any additional information:

        - Patient Name: [Extracted Name]
        - Patient Identifier: [Extracted Identifier]
        - Doctor Name: [Extracted Name]
        - Doctor Identifier: [Extracted Identifier]
        - Date of Issuance: [Extracted Date]
        """  # noqa: E501

    model = Ollama(model='gemma2', temperature=0.0)
    text = model.invoke(prompt)
    print(text)

    prompt = """
        ### Template:
        {
            'PatientName': "",
            'PatientIdentifier': "",
            'DoctorName': "",
            'DoctorIdentifier': "",
            'DateOfIssuance': ""
        }

        ### Example:
        {
            'PatientName': "Ana Oliveira",
            'PatientIdentifier': "987.654.321-00",
            'DoctorName': "Dr. João Silva",
            'DoctorIdentifier': "CRM-12345",
            'DateOfIssuance': "2024-10-11"
        }

        ### Text:
        """
    prompt += text
    model = Ollama(model='nuextract', temperature=0.0)
    text = model.invoke(prompt)

    print(text)
    metadata = parse_metadata(text)
    metadata['PatientIdentifier'] = sanitize_text(
        metadata['PatientIdentifier']
    )
    metadata['DoctorIdentifier'] = sanitize_text(metadata['DoctorIdentifier'])

    with Connection() as conn:
        SCRIPT_SQL = """
            SELECT patient_id FROM patients WHERE identifier = %(PatientIdentifier)s;
        """
        registry = conn.select(SCRIPT_SQL, metadata)

        if not registry:
            SCRIPT_SQL = """
                INSERT INTO patients (name, identifier)
                VALUES (%(PatientName)s, %(PatientIdentifier)s)
                RETURNING patient_id;
            """
            registry = conn.exec_with_result(SCRIPT_SQL, metadata)
        patient_id = registry[0][0]

        SCRIPT_SQL = """
            SELECT doctor_id FROM doctors WHERE identifier = %(DoctorIdentifier)s;
        """
        doctor_id = conn.select(SCRIPT_SQL, metadata)

        if not doctor_id:
            SCRIPT_SQL = """
                INSERT INTO doctors (name, identifier)
                VALUES (%(DoctorName)s, %(DoctorIdentifier)s)
                RETURNING doctor_id;
            """
            doctor_id = conn.exec_with_result(SCRIPT_SQL, metadata)
        doctor_id = doctor_id[0][0]

        SCRIPT_SQL = """
            UPDATE documents
            SET patient_id = %(patient_id)s,
                doctor_id = %(doctor_id)s,
                date_of_issuance = %(DateOfIssuance)s
            WHERE document_id = %(document_id)s;
            """
        conn.exec(
            SCRIPT_SQL,
            {
                'patient_id': patient_id,
                'doctor_id': doctor_id,
                'DateOfIssuance': metadata['DateOfIssuance'],
                'document_id': document_id,
            },
        )


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
