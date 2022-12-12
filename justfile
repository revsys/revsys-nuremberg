# vim: filetype=just tabstop=4 shiftwidth=4 expandtab number
set dotenv-load := false
IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
CACHE_REGISTRY := 'registry.revsys.com/cache/nuremberg'
VERSION := 'v0.3.9'

set shell := ["/bin/bash", "-c"]

list:
    just --list

version:
    @echo {{VERSION}}

tag:
    @echo {{IMAGE_REGISTRY}}:{{VERSION}}

# rebuild requirements files
regen-requirements:
  pip-compile web/requirements.in -o web/requirements.txt
  pip-compile <( head -n$( grep -n "# Dev" web/requirements.in | cut -d":" -f1 ) web/requirements.in  ) -o web/requirements.prod.txt


_test-packages:
  @tail -n  $( echo $(( $( wc -l web/requirements.in | cut -d" " -f1 ) - $( grep -nie '^#[[:blank:]]*test' web/requirements.in  | cut -d":" -f1) ))  ) web/requirements.in

build step='release' action='--load':
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

    docker buildx build --progress plain ${cache} {{action}} -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .
    [[ "{{ step }}" == "release" ]] && docker tag {{IMAGE_REGISTRY}}:${endbits} {{IMAGE_REGISTRY}}:last
    just _bk-down

push step='release': (build step)
    #!/usr/bin/env bash
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    just build {{step}} --push

regen-solr-image:
    just solr-dc down -v
    just solr-dc up -d --quiet-pull solr-loader || ( just build release && just regen-solr-image )
    SOLR_NO_RESTORE=1 SOLR_BUILD=1 ./init.sh
    just solr-dc up -d --quiet-pull solr-data-load
    SOLR_RESTORE_SNAPSHOT= SOLR_DIST_DATA=1 SOLR_BUILD=1 ./init.sh || exit 1
    just build solr
    docker tag {{IMAGE_REGISTRY}}:{{VERSION}}-solr {{IMAGE_REGISTRY}}:last-solr
    just push solr
    docker push {{IMAGE_REGISTRY}}:last-solr

# fs path to solr-image-build compose file
solr-compose: _solr-compose
_solr-compose:
    @echo {{justfile_directory()}}/docker-compose.solr-build.yml

# shortcut for interacting w/ the solr image-build docker-compose project
solr-dc *args='ps':
    docker-compose -f $( just solr-compose ) -p solrbld {{args}}

# shortcut for interacting w/ the CI docker-compose project
ci-dc *args='ps':
    docker-compose -f ./docker-compose.yml -f ./docker-compose.override.yml -f ./docker-compose.ci.yml {{args}}

# target for running tests IN CI
test:
    docker inspect $( just tag )-tester >& /dev/null || just build tester
    just ci-dc up -d --quiet-pull
    just ci-dc exec -u0  web find /tmp /nuremberg /code -type f -not -user ${UID} -exec chown -Rv $UID {} +  | wc -l
    just ci-dc up -d --quiet-pull selenium solr
    just ci-dc exec -u$UID web pytest || exit 1
    just ci-dc exec -u$UID web pytest --no-cov nuremberg/documents/browser_tests.py || exit 1


deploy env='dev':
    @git tag -f last/{{env}}/deploy {{env}}/deploy
    @git tag -f {{env}}/deploy {{VERSION}}
    @git push --tags --force

_bk-up:
    #!/bin/bash
    set -o pipefail
    [[ -n $( docker buildx ls | grep 'default.*docker' ) ]] &&
        docker buildx create --platform linux/amd64 --bootstrap --name nuremberg-builder >& /dev/null
        docker buildx use nuremberg-builder

_bk-down:
    docker buildx use default
    docker buildx stop nuremberg-builder

