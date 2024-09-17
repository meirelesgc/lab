#!/bin/bash

poetry run uvicorn lab:app --host 0.0.0.0 --port 8000 --reload &

poetry run celery -A lab.routers.documents.celery worker --loglevel=INFO --concurrency=2 --uid=nobody&

poetry run celery -A lab.routers.documents.celery flower --uid=nobody &

wait -n