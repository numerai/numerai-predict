FROM python:3.11-slim

RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        build-essential \
        cmake \
        git \
        python3-dev

COPY ./requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./predict.py .
ENTRYPOINT ["python", "predict.py"]
