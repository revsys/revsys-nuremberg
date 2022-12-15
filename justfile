# vim: filetype=just tabstop=4 shiftwidth=4 expandtab number
set dotenv-load := false
IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
CACHE_REGISTRY := 'registry.revsys.com/cache/nuremberg'
VERSION := 'v0.3.11r2'

set shell := ["/bin/bash", "-c"]

list:
    just --list


# display image layer names (e.g.: just build [name])
layers:
    @echo -en "\nDockerfile layers:\n\n"; sed -Ene '/^FROM/s/^FROM.*as (.*)$/\t\1/p' Dockerfile

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

# build [step], tag it with {{IMAGE_REGISTRY}}:{{VERSION}}-{{step}} except for release target
build step='release' action='--load' verbosity='':
    #!/usr/bin/env bash
    #set -o xtrace
    just _bk-up
    if [[ "{{ step }}" == "release" ]];
    then
        endbits={{VERSION}}
        cendbits=last
    else
        endbits={{VERSION}}-{{ step }}
        cendbits=last-{{step}}
    fi

    [[ -n "{{verbosity}}" ]] && verbosity="--progress plain" || verbosity="--quiet"

    cache="--cache-from {{CACHE_REGISTRY}}:last --cache-from {{CACHE_REGISTRY}}:${cendbits} --cache-to type=registry,dest={{CACHE_REGISTRY}}:${cendbits},mode=max"
    [[ "{{step}}" == "tester" ]] && cache="--cache-from {{CACHE_REGISTRY}}:last"

    echo "Building {{IMAGE_REGISTRY}}:${endbits}"

    docker buildx build ${verbosity} ${cache} {{action}} -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} . ||
        docker buildx build --progress plain ${cache} {{action}} -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .

    [[ "{{ step }}" == "release" ]] && docker tag {{IMAGE_REGISTRY}}:${endbits} {{IMAGE_REGISTRY}}:last
    just _bk-down

# push image to registry
push step='release':
    #!/usr/bin/env bash
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    just build {{step}} --push

# execute new solr image build process
@regen-solr-image:
    just solr-dc down -v >& /dev/null
    docker inspect $( just tag ) >& /dev/null || ( just build release && just regen-solr-image )
    just solr-dc up -d --quiet-pull solr-loader || ( just build release && just regen-solr-image )
    @SOLR_NO_RESTORE=1 SOLR_BUILD=1 ./init.sh
    just solr-dc up -d --quiet-pull solr-data-load
    @SOLR_RESTORE_SNAPSHOT= SOLR_DIST_DATA=1 SOLR_BUILD=1 ./init.sh || exit 1
    just build solr
    docker tag {{IMAGE_REGISTRY}}:{{VERSION}}-solr {{IMAGE_REGISTRY}}:last-solr
    just push solr
    docker push {{IMAGE_REGISTRY}}:last-solr

# fs path to solr-image-build compose file
@solr-compose: _solr-compose
_solr-compose:
    @echo {{justfile_directory()}}/docker-compose.solr-build.yml

# shortcut for interacting w/ the solr image-build docker-compose project
@solr-dc *args='ps':
    docker-compose -f $( just solr-compose ) -p solrbld {{args}}

# shortcut for interacting w/ the CI docker-compose project
@ci-dc *args='ps':
    docker-compose -f ./docker-compose.yml -f ./docker-compose.override.yml -f ./docker-compose.ci.yml -p ci {{args}}

# target for running tests IN CI
@test:
    docker inspect $( just tag )-tester >& /dev/null || just build tester
    just ci-dc up -d --quiet-pull
    just ci-dc exec -u0  web find /tmp /nuremberg /code -type f -not -user ${UID} -exec chown -Rv $UID {} +  | wc -l
    @just ci-dc exec -u$UID web pytest || exit 1
    @just ci-dc exec -u$UID web pytest --no-cov nuremberg/documents/browser_tests.py || exit 1
    just ci-dc down -v

# executes bump2version on local repository (e.g.: just bump patch; just bump build)
@bump part='build' args='':
    docker inspect registry.revsys.com/bump2version >& /dev/null || ( just _make-bv && just bump {{part}} )
    docker run -u ${UID} --rm -v $PWD:/code --workdir /code registry.revsys.com/bump2version {{part}} {{args}} || exit 1


# updates last/{{env}}/deploy and {{env}}/deploy tags to trigger flux deployment
@deploy env='dev':
    git tag -f last/{{env}}/deploy {{env}}/deploy
    git tag -f {{env}}/deploy {{VERSION}}
    git push --tags --force

@_make-bv:
    just build b2v
    docker tag $( just tag )-b2v registry.revsys.com/bump2version
    docker push registry.revsys.com/bump2version > /dev/null

_bk-up:
    #!/bin/bash
    set -o pipefail
    [[ -n $( docker buildx ls | grep 'default.*docker' ) ]] &&
        docker buildx create --platform linux/amd64 --bootstrap --name nuremberg-builder >& /dev/null
        docker buildx use nuremberg-builder

@_bk-down:
    docker buildx use default
    docker buildx stop nuremberg-builder

# target that wraps simple strings with figlet(6)
# e.g.: just banner version
banner args='':
    #!/usr/bin/env bash
    docker inspect registry.revsys.com/bump2version >& /dev/null || (
        docker pull registry.revsys.com/bump2version >& /dev/null || (
            just _make-bv && just banner {{args}}
        )
    )
    just _figlet $( just {{args}} )

_figlet args='':
    #!/usr/bin/env bash
    docker run --entrypoint figlet --rm registry.revsys.com/bump2version -c -f standard -m0 -w115 {{args}}


