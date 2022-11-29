#vim: ft=just ts=4 sw=4 et
set dotenv-load := false
IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
VERSION := 'v0.2.5'

set shell := ["/bin/bash", "-c"]

list:
    just --list

# rebuild requirements files
regen-requirements:
  pip-compile web/requirements.in -o web/requirements.txt
  pip-compile <( head -n$( grep -n "# Dev" web/requirements.in | cut -d":" -f1 ) web/requirements.in  ) -o web/requirements.prod.txt

build step='release':
    #!/usr/bin/env bash
    echo "step={{ step }}"
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    docker buildx build -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .

push step='release': (build step)
    #!/usr/bin/env bash
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    docker push {{IMAGE_REGISTRY}}:${endbits}

deploy:
    @helm upgrade -i hlsnp --namespace nuremberg chart/

regen-solr-image:
    #!/usr/bin/env bash
    set -o xtrace verbose
    rm -rf /tmp/solr_data; mkdir /tmp/solr_data
    docker-compose up -d --force-recreate solr
    SOLR_RESTORE_SNAPSHOT=1 SOLR_DIST_DATA=1./init.sh
    just push solr
