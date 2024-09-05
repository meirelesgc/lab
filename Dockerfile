FROM python:3.12-slim
ENV POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app
COPY . .

RUN pip install poetry

RUN poetry config installer.max-workers 10
RUN poetry install --no-interaction --no-ansi
RUN poetry run spacy download pt_core_news_lg

EXPOSE 8000
EXPOSE 5672

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
