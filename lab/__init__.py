from dotenv import load_dotenv
from fastapi import FastAPI

from lab.routers import documents, openAI, parameters, patient

load_dotenv()

app = FastAPI()
app.include_router(openAI.router)
app.include_router(documents.router)
app.include_router(parameters.router)
app.include_router(patient.router)
