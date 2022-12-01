# vim: ft=just ts=4 sw=4 et
set dotenv-load := false
IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
CACHE_REGISTRY := 'registry.revsys.com/cache/nuremberg'
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
    set -o xtrace
    just _bk-up
    echo "step={{ step }}"
    if [[ "{{ step }}" == "release" ]];
    then
        endbits={{VERSION}}
        cendbits=last 
    else
       endbits={{VERSION}}-{{ step }}
       cendbits=last-{{ step }}
    fi

    cache="--cache-from {{CACHE_REGISTRY}}:${cendbits} --cache-to {{CACHE_REGISTRY}}:${cendbits}"

    docker buildx build ${cache} --load -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .
    [[ "{{ step }}" == "release" ]] && docker tag {{IMAGE_REGISTRY}}:${endbits} {{IMAGE_REGISTRY}}:last
    just _bk-down

push step='release': (build step)
    #!/usr/bin/env bash
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    docker push {{IMAGE_REGISTRY}}:${endbits}

deploy:
    @helm upgrade -i hlsnp --namespace nuremberg chart/

regen-solr-image:
    #!/usr/bin/env bash
    set -o xtrace verbose pipefail
    docker-compose up -d --force-recreate solr &&
    SOLR_NO_RESTORE=1 ./init.sh 
    docker-compose up -d web || ( just build && docker-compose up -d web )
    SOLR_RESTORE_SNAPSHOT= SOLR_DIST_DATA=1 ./init.sh
    just build solr

_bk-up:
    #!/bin/bash
    set -o pipefail
    [[ -n $( docker buildx ls | grep 'default.*docker' ) ]] &&
        docker buildx create --platform linux/amd64 --bootstrap --name nuremberg-builder >& /dev/null 
        docker buildx use nuremberg-builder

_bk-down:
    docker buildx use default
    docker buildx stop nuremberg-builder

