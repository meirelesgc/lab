from uuid import UUID

from fastapi import APIRouter

from lab.models import Message, Patient

from ..dao.dao_patient import add_patient, delete_patient, select_patients

router = APIRouter(tags=['Patients'])


@router.post('/patient', response_model=Patient)
def create_patient(name: str):
    patient = add_patient(name)
    return patient


@router.get('/patient', response_model=list[Patient])
def consult_patients():
    patients = select_patients()
    return patients


@router.delete('/patient/{patient_id}', response_model=Message)
def remove_patient(patient_id: UUID):
    delete_patient(patient_id)
    return {'message': 'Patient deleted!'}
