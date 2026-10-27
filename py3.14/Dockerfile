FROM python:3.14-slim

RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    python3-dev \
    python3-pip \
    python3-venv \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir poetry==2.1.3

ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:$PATH"

COPY ./py3.14/pyproject.toml ./pyproject.toml
COPY ./py3.14/poetry.lock ./poetry.lock

RUN poetry config virtualenvs.create false \
    && poetry config installer.parallel false \
    && poetry config requests.max-retries 5 \
    && poetry install --no-interaction --no-ansi \
    && rm -rf /root/.cache/pypoetry /root/.cache/pip

COPY ./predict.py .

ARG GIT_REF
ENV GIT_REF=$GIT_REF

ENTRYPOINT ["python", "predict.py"]
