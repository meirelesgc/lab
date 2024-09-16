from ..dao import Connection
from ..models import Patient


def add_patient(name):
    patient = Patient(name=name)
    SCRIPT_SQL = """
        INSERT INTO patients (patient_id, name)
        VALUES (%(patient_id)s, %(name)s);
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, patient.model_dump())
    return patient


def select_patients():
    SCRIPT_SQL = """
        SELECT patient_id, name
        FROM patients;
        """
    with Connection() as conn:
        registry = conn.select(SCRIPT_SQL)
    patient_list = []
    if registry:
        for patient_id, name in registry:
            patient_list.append(Patient(patient_id=patient_id, name=name))
    return patient_list


def delete_patient(patient_id):
    SCRIPT_SQL = """
        DELETE FROM patients
        WHERE patient_id = %(patient_id)s;
        """
    with Connection() as conn:
        conn.exec(SCRIPT_SQL, {'patient_id': patient_id})
