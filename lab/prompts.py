PATIENT_METADATA_SCHEMA = """
{
    "name": "",
    "CPF": "",
    "RG": "",
    "ID": ""
}
"""
PATIENT_EX1 = """
{
    "name": "Carlos Mendes",
    "CPF": "321.654.987-00",
    "RG": "12.345.678-9",
    "ID": "001"
}
"""
PATIENT_EX2 = """
{
    "name": "Julia Santos",
    "CPF": "456.789.123-00",
    "RG": "98.765.432-1",
    "ID": "002"
}
"""
PATIENT_EX3 = """
{
    "name": "Roberto Lima",
    "CPF": "123.987.456-00",
    "RG": "56.123.789-0",
    "ID": "003"
}
"""
PATIENT_METADATA_EXAMPLE = [PATIENT_EX1, PATIENT_EX2, PATIENT_EX3]

DATE_METADATA_SCHEMA = """
{
    "date": ""
}
"""

DATE_EX1 = """
{
    "date": "09/10/2022"
}
"""

DATE_EX2 = """
{
    "date": "03/12/2023"
}
"""

DATE_EX3 = """
{
    "date": "15/07/1990"
}
"""

DATE_METADATA_EXAMPLE = [DATE_EX1, DATE_EX2, DATE_EX3]

CLEAR_TEXT_PROMPT = """
{content}

---

Utilize o texto acima como referência, sem modificar o formato ou conteúdo além do solicitado.

Instruções de Substituição:

Substituições a serem realizadas:
Remova datas e substitua pelo token <DATE>.
Remova nomes de pessoas e substitua pelo token <NOME>.
Remova nomes de instituições e substitua pelo token <ENTITY_NAME>.
Remova identificações de médicos e substitua pelo token <DOCTOR>.
Remova códigos de identificação de pessoas (CPF, RG, CRM) e substitua pelo token <PERSON_ID>.

Exemplo de Substituição:
Antes: Paciente João da Silva, 35 anos, deu entrada no Hospital São Lucas no dia 12/03/2023 com queixa de dores abdominais.
Depois: Paciente <NOME>, 35 anos, procurou <ENTITY_NAME> em <DATE> com queixa de dor abdominal.

Notas Importantes:
Se não houver elementos a serem substituídos, mantenha o texto inalterado.
Preserve os sintomas e detalhes clínicos do texto original.
Priorize a coesão e legibilidade do texto durante a substituição.
Manter a integridade e clareza do texto original para análise ou formação
"""
