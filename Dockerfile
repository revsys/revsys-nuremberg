#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM rust:alpine as just-builder
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV VERSION v0.9.4

#RUN apt update; apt -y install git --no-install-recommends
RUN apk add git musl-dev
RUN git clone https://github.com/casey/just /just

WORKDIR /just

RUN git checkout ${VERSION}


RUN RUSTFLAGS='-C target-feature=+crt-static' cargo build --release --target x86_64-unknown-linux-musl

RUN cp target/*/release/just /bin/


#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM alpine as just
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

COPY --from=just-builder /bin/just /

#ENTRYPOINT ["/bin/sh", "-c"]

LABEL org.opencontainers.image.source https://github.com/revsys/revsys-nuremberg

ENTRYPOINT  ["/bin/sh", "-c"]
CMD ["install -v -m 0755 -t /dist /just && /just --version"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM python:3.10-alpine as b2v
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

RUN apk --no-cache add git figlet

RUN --mount=type=cache,target=/root/.cache \
    pip install bump2version

RUN git config --system user.email ci@revsys.com
RUN git config --system user.name "REVSYS CI"
RUN git config --system --add safe.directory /code
RUN git config --system init.defaultBranch main

ENTRYPOINT ["bump2version"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM registry.revsys.com/just as j
FROM revolutionsystems/python:3.10-wee-lto-optimized as runner
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV PYTHON_PATH /code
ENV PATH /.venv/bin:/node/bin:${PATH}

COPY --from=j /just /usr/bin/just

WORKDIR /code

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM runner as builder
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-


SHELL ["/bin/bash", "-c"]

RUN python -m venv /.venv; \
    mkdir -p /{c,n}ode/data


RUN apt update; apt -y install curl

RUN  tar -xzC /node --strip-components=1 -f <( curl -sL https://nodejs.org/dist/v18.12.1/node-v18.12.1-linux-x64.tar.gz )

RUN --mount=type=bind,source=web/requirements.prod.txt,target=/requirements.txt \
    pip install -r /requirements.txt

WORKDIR /node

RUN /node/bin/npm install less

WORKDIR /code

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM builder as release
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV DJANGO_SETTINGS_MODULE nuremberg.settings
ENV BASE_DIR=/code
ENV IMAGE_VERSION v0.5.20

RUN ln -s /node/node_modules/less/bin/lessc /bin/lessc

COPY dumps/nuremberg_prod_dump_latest.sqlite3.zip /code/data/

COPY web/nuremberg /code/nuremberg
COPY web/manage.py /code
COPY solr_conf /code/solr_conf

RUN touch /code/nuremberg/__init__.py; \
    chown 1000 /code

USER 1000

WORKDIR /code

ENTRYPOINT ["/.venv/bin/gunicorn"]
CMD ["-b", ":8000", "nuremberg.wsgi:application"]

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM release as tester
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

USER 0

ENV SECRET_KEY xx
ENV SOLR_URL http://solr:8983/solr/nuremberg_dev
ENV DJANGO_SETTINGS_MODULE nuremberg.test_settings
ENV SQLITE_DB_PATH /tmp/nuremberg_dev.db
ENV pytest_github_report true

COPY web/requirements.in web/requirements.in
COPY justfile /code/

RUN --mount=type=cache,target=/root/.cache \
    pip install $( just _test-packages ) pytest-github-report

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
FROM solr:8.11-slim as solr
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV SOLR_CORE nuremberg_dev

COPY solr_conf /opt/solr-8.11.2/solr_conf

ENV IMAGE_VERSION v0.5.20-solr

RUN --mount=type=bind,source=./dist/var-solr.tgz,target=/mnt/var-solr.tgz \
    cd / && \
    tar xvfpz /mnt/var-solr.tgz
