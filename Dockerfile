#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM python:3.11-alpine as b2v
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED 1

RUN apk --no-cache add git figlet

RUN --mount=type=cache,target=/root/.cache \
    pip install bump2version

RUN git config --system user.email ci@revsys.com
RUN git config --system user.name "REVSYS CI"
RUN git config --system --add safe.directory /code
RUN git config --system init.defaultBranch main

ENTRYPOINT ["bump2version"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM revolutionsystems/python:3.11-wee-lto-optimized as runner
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED 1
ENV PYTHON_PATH /code
ENV PATH /.venv/bin:/node/bin:${PATH}

WORKDIR /code

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM runner as builder
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-


ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED 1

SHELL ["/bin/bash", "-c"]

RUN python -m venv /.venv; \
    mkdir -p /{c,n}ode/data


RUN apt update; apt -y install curl

#RUN  tar -xzC /node --strip-components=1 -f <( curl -sL https://nodejs.org/dist/v18.12.1/node-v18.12.1-linux-x64.tar.gz )
WORKDIR /node
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g less

RUN --mount=type=cache,target=/root/.cache pip install -U pip

RUN --mount=type=bind,source=web/requirements.txt,target=/requirements.txt \
    pip install -r /requirements.txt


WORKDIR /code

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM builder as release
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE nuremberg.settings
ENV BASE_DIR=/code
ENV IMAGE_VERSION v0.5.133


#RUN ln -s /node/node_modules/less/bin/lessc /bin/lessc

COPY dumps/nuremberg_prod_dump_latest.sqlite3.zip /code/data/

COPY web/nuremberg /code/nuremberg
COPY web/frontend /code/frontend
COPY web/manage.py /code
COPY solr_conf /code/solr_conf

RUN touch /code/nuremberg/__init__.py; \
    chown 1000 /code

USER 1000

WORKDIR /code

CMD ["/.venv/bin/gunicorn", "-b", ":8000", "nuremberg.wsgi:application"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM release as tester
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

USER 0

ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED 1
ENV SECRET_KEY xx
ENV SOLR_URL http://solr:8983/solr/nuremberg_dev
ENV DJANGO_SETTINGS_MODULE nuremberg.test_settings
ENV SQLITE_DB_PATH /tmp/nuremberg_dev.db
ENV pytest_github_report true

COPY justfile /code/

RUN pip install pytest-github-report
RUN python -m zipfile -e /code/data/nuremberg_prod_dump_latest.sqlite3.zip /tmp

RUN ./manage.py collectstatic; chmod -R 777 /code/static
RUN ./manage.py migrate


ENTRYPOINT ["pytest"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM alpine as cacher
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

RUN apk add --no-cache rsync; mkdir /.cache

COPY .cache/* /.cache/

RUN find /.cache -type f -exec chmod -v 666 {} +

ENTRYPOINT ["/bin/sh", "-c"]

CMD ["rsync -varHpDtSl --exclude=/.cache/keep /.cache/* /mnt/. || true"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM solr:9.2.0 as solr
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV SOLR_CORE nuremberg_dev

COPY solr_conf /opt/solr-9.2.0/solr_conf


ENV IMAGE_VERSION v0.5.133-solr


RUN --mount=type=bind,source=./dist/var-solr.tgz,target=/mnt/var-solr.tgz \
    cd / && \
    tar xvfpz /mnt/var-solr.tgz
