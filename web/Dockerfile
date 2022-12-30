FROM python:3.10 as release

RUN mkdir /nuremberg
WORKDIR /nuremberg

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_SRC=/usr/local/src

ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED 1

# Get Node 18 instead of version in APT repository.
# Downloads an installation script, which ends by running
# apt-get update: no need to re-run at this layer
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g less

RUN apt install sqlite3

COPY requirements.txt ./requirements.txt
RUN pip install -U pip \
    && pip install -r requirements.txt \
    && rm requirements.txt
