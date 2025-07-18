FROM python:3.10-slim

ARG GIT_REF
ENV GIT_REF=$GIT_REF
RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        build-essential \
        cmake \
        git \
        python3-dev

COPY ./py3.10/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./redict.py .
ENTRYPOINT ["python", "predict.py"]
