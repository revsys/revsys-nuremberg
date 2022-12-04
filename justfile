# vim: ft=just ts=4 sw=4 et
set dotenv-load := false
IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
CACHE_REGISTRY := 'registry.revsys.com/cache/nuremberg'
VERSION := 'v0.2.7'

set shell := ["/bin/bash", "-c"]

list:
    just --list

# rebuild requirements files
regen-requirements:
  pip-compile web/requirements.in -o web/requirements.txt
  pip-compile <( head -n$( grep -n "# Dev" web/requirements.in | cut -d":" -f1 ) web/requirements.in  ) -o web/requirements.prod.txt


_test-packages:
  @tail -n  $( echo $(( $( wc -l web/requirements.in | cut -d" " -f1 ) - $( grep -nie '^#[[:blank:]]*test' web/requirements.in  | cut -d":" -f1) ))  ) web/requirements.in

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
        cendbits=last-{{step}}
    fi

    cache="--cache-from {{CACHE_REGISTRY}}:last --cache-from {{CACHE_REGISTRY}}:${cendbits} --cache-to type=registry,dest={{CACHE_REGISTRY}}:${cendbits},mode=max"
    [[ "{{step}}" == "tester" ]] && cache="--cache-from {{CACHE_REGISTRY}}:last"

    docker buildx build --progress plain ${cache} --load -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .
    [[ "{{ step }}" == "release" ]] && docker tag {{IMAGE_REGISTRY}}:${endbits} {{IMAGE_REGISTRY}}:last
    just _bk-down

push step='release': (build step)
    #!/usr/bin/env bash
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    docker push {{IMAGE_REGISTRY}}:${endbits}

regen-solr-image:
    #!/usr/bin/env bash
    set -o xtrace verbose pipefail
    docker-compose -f $( just _solr-compose ) -p solrbld up -d --force-recreate solr-data-load && \
    SOLR_NO_RESTORE=1 SOLR_BUILD=1 ./init.sh && \
    docker-compose -f $( just _solr-compose ) -p solrbld up -d solr-loader || \
    ( just build && docker-compose -f $( just _solr-compose ) -p solrbld up  -d solr-loader ) && \
    SOLR_RESTORE_SNAPSHOT= SOLR_DIST_DATA=1 SOLR_BUILD=1 ./init.sh && \
    just build solr && \
    docker tag {{IMAGE_REGISTRY}}:{{VERSION}}-solr {{IMAGE_REGISTRY}}:last-solr && \
    just push solr && \
    docker push {{IMAGE_REGISTRY}}:last-solr || exit 1

# fs path to solr-image-build compose file
solr-compose: _solr-compose
_solr-compose:
    @echo {{justfile_directory()}}/docker-compose.solr-build.yml

test:
    @docker-compose -f ./docker-compose.yml -f ./docker-compose.override.yml -f ./docker-compose.ci.yml up --quiet-pull -d
    docker-compose exec -u1000 web pytest || exit 1
    docker-compose exec -u1000 web pytest --no-cov nuremberg/documents/browser_tests.py || exit 1

_bk-up:
    #!/bin/bash
    set -o pipefail
    [[ -n $( docker buildx ls | grep 'default.*docker' ) ]] &&
        docker buildx create --platform linux/amd64 --bootstrap --name nuremberg-builder >& /dev/null 
        docker buildx use nuremberg-builder

_bk-down:
    docker buildx use default
    docker buildx stop nuremberg-builder

