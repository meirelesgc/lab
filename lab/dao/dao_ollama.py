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

    return text


def parse_metadata(text):
    print('!!!VALOR INICIAL!!!', text, '--' * 10)

    try:
        end = text.rfind('}')
        start = text.rfind('{', 0, end)

        if start != -1 and end != -1:
            json_text = text[start : end + 1]
            print(json_text.replace("'", '"'))
            metadata_dict = json.loads(json_text.replace("'", '"'))
            print('!!!VALOR FINAL!!!', metadata_dict)
            return metadata_dict
        else:
            print('Chaves JSON não encontradas corretamente')
            return None
    except json.JSONDecodeError as e:
        print(f'Erro ao converter JSON: {e}')
        return None


def add_database_metadata(document_id):
    text = document_to_text(document_id)
    text = str(' ').join(text)

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

    model = OllamaLLM(model='gemma2')
    text = model.invoke(prompt)

    prompt = """
<|input|>
### Template:
{
    "patient_name": "",
    "patient_identifier": "",
    "doctor_name": "",
    "doctor_identifier": "",
    "date_issuance": ""
}

### Example:
{
    "patient_name": "Ana Oliveira",
    "patient_identifier": "987.654.321-00",
    "doctor_name": "Dr. João Silva",
    "doctor_identifier": "12345",
    "date_issuance": "2024-10-11"
}

### Text:
"""
    prompt += text

    model = OllamaLLM(model='nuextract')
    text = model.invoke(prompt)

    metadata = parse_metadata(text)
    with Connection() as conn:
        if metadata and metadata['patient_name']:
            SCRIPT_SQL = """
                SELECT patient_id, identifier
                FROM public.patients
                WHERE SIMILARITY(identifier, %(identifier)s) > 0.7
                ORDER BY SIMILARITY(identifier, %(identifier)s) DESC
                LIMIT 1;
                """

            similar_patient = conn.select(
                SCRIPT_SQL, {'identifier': str(metadata)}
            )

            if similar_patient:
                print(f'Paciente já existe com ID: {similar_patient[0]}')
            else:
                SCRIPT_SQL = """
                    INSERT INTO public.patients
                    (name, identifier)
                    VALUES (%(name)s, %(identifier)s);
                    """
                conn.exec(
                    SCRIPT_SQL,
                    {
                        'name': metadata['patient_name'],
                        'identifier': str(metadata),
                    },
                )


def sanitize_text(text):
    text = unidecode(text)
    return ''.join(char for char in text if char.isalnum())


def add_database_text(document_id):
    documents = document_to_text(document_id)

    text = str()
    for document in documents:
        prompt = f"""
            {document}

            Use the previous text as a reference. Do not change the format or content other than what is requested.

            **Replacement Instructions:**
            1. **Replacements to be made:**
            - Remove any date and replace it with the <DATE> token.
            - Remove any person's name and replace it with the <NAME> token.
            - Remove any institution name and replace it with the <ENTITY_NAME> token.
            - Remove any doctor's name or identification and replace it with the <DOCTOR> token.
            - Remove any person's identification code (CPF, RG, CRM) and replace it with the <PERSON_ID> token.

            **Replacement Example:**
            - Before: Patient João da Silva, 35 years old, went to Hospital São Lucas on 03/12/2023 with complaints of abdominal pain.
            - After: Patient <NAME>, 35 years old, went to <ENTITY_NAME> on <DATE> with complaints of abdominal pain.

            **Important Notes:**
            - If there are no elements to be replaced, do not make any changes.
            - Keep the symptoms and clinical details in the original text.
            - Prioritize preserving the cohesion and readability of the text during the replacement process.

            **Objective:**
            The purpose of this prompt is to ensure the anonymization of sensitive data, while maintaining the integrity and clarity of the original text, allowing its use in analysis or training contexts without compromising privacy.
            """

        text += OllamaLLM(model='gemma2').invoke(prompt)

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
