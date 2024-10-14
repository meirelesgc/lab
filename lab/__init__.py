import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE: str
    PG_USER: str
    PASSWORD: str
    HOST: str
    PORT: str
    OPENAI_API_KEY: str
    BROKER: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
os.environ.update(settings.model_dump())


from lab.routers import documents, openAI, parameters, patient  # noqa: E402

app = FastAPI()

origins = [
    'http://localhost',
    'http://localhost:5173',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(openAI.router)
app.include_router(documents.router)
app.include_router(parameters.router)
app.include_router(patient.router)
