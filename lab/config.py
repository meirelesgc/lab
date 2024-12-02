from typing import Optional

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE: str = 'lab'
    PG_USER: str = 'postgres'
    PASSWORD: str = 'postgres'
    HOST: str = 'localhost'
    PORT: int = 5432
    OPENAI_API_KEY: Optional[str] = None
    BROKER: str = 'pyamqp://guest@localhost//'
    OLLAMA_HOST: str = 'http://localhost:11434'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

    @validator('OPENAI_API_KEY', pre=True, always=True)
    def check_openai_key(cls, v):
        if v is None:
            raise ValueError(
                'OPENAI_API_KEY is required for production environments'
            )
        return v


settings = Settings()
