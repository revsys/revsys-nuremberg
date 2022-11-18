#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM revolutionsystems/python:3.10-wee-lto-optimized as runner
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV PYTHON_PATH /code
ENV PATH /.venv/bin:/node/bin:${PATH}

WORKDIR /code

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM runner as builder
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-


SHELL ["/bin/bash", "-c"]
RUN python -m venv /.venv; \
    mkdir -p /{c,n}ode/data
    

RUN apt update; apt -y install curl

RUN --mount=type=bind,source=web/requirements.prod.txt,target=/requirements.txt \
    pip install -r /requirements.txt


RUN  tar -xzC /node --strip-components=1 -f <( curl -sL https://nodejs.org/dist/v18.12.1/node-v18.12.1-linux-x64.tar.gz )

WORKDIR /node

RUN /node/bin/npm install less

#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-
FROM runner as release
#.--.---.-.-.-.-.----.-..-.---..-------.-.--.-.-..-.-.-.-.-.-..--.-

ENV DJANGO_SETTINGS_MODULE nuremberg.settings
ENV BASE_DIR=/code
ENV IMAGE_VERSION v0.0.0

RUN ln -s /node/node_modules/less/bin/lessc /bin/lessc

COPY --from=builder /.venv /.venv
COPY --from=builder /node /node

COPY dumps/nuremberg_prod_dump_latest.sqlite3.zip /code/data/
COPY dumps/nuremberg_solr_snapshot_latest.tar.gz /code/data/

COPY web/nuremberg /code/nuremberg
COPY web/manage.py /code

