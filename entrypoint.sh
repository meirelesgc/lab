#!/bin/bash

poetry run uvicorn lab:app --host 0.0.0.0 --port 8000 --reload &

poetry celery -A lab.routers.documents.celery worker --loglevel=INFO --concurrency=1 &

poetry run celery -A lab.celery flower &

wait -n