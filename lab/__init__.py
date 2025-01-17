from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lab.routers import admin, documents, parameters, patient

app = FastAPI()

origins = [
    'http://localhost/',
    'http://localhost:5173/',
    'http://lab-front:80/',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(documents.router)
app.include_router(parameters.router)
app.include_router(patient.router)
app.include_router(admin.router)
