FROM python:3.11-slim

ARG GIT_REF
ENV GIT_REF=$GIT_REF

RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    python3-dev \
    python3-pip \
    python3-venv \
    libffi-dev

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir poetry==2.1.3

ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:$PATH"

COPY ./py3.11/pyproject.toml ./pyproject.toml
COPY ./py3.11/poetry.lock ./poetry.lock

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY ./predict.py .

ENTRYPOINT ["python", "predict.py"]
