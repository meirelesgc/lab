from celery import Celery

from .config import settings

celery = Celery(
    broker=settings.BROKER,
    broker_connection_retry_on_startup=True,
)
