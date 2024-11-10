from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lab.routers import documents, ollama, parameters, patient

app = FastAPI()

origins = ['http://localhost', 'http://localhost:5173']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(ollama.router)
app.include_router(documents.router)
app.include_router(parameters.router)
app.include_router(patient.router)
