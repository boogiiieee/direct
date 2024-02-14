FROM python:3.11

WORKDIR /app

COPY poetry.lock pyproject.toml ./

RUN pip install poetry
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-root

COPY . /app
