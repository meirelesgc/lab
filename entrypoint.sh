#!/bin/bash

poetry run uvicorn lab:app --host 0.0.0.0 --port 8000 --reload &

poetry run celery -A lab.celery worker --loglevel=INFO --concurrency=1 &

poetry run celery -A lab.celery flower &

wait -n