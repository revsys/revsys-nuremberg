# vim: filetype=just tabstop=4 shiftwidth=4 expandtab number
# poke 10
set dotenv-load := false

IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
CACHE_REGISTRY := env_var_or_default('CACHE_REGISTRY', 'registry.revsys.com/cache/nuremberg')


VERSION := 'v0.5.115'


GITHUB_STEP_SUMMARY := env_var_or_default('GITHUB_STEP_SUMMARY', '')
NO_CACHE_TO := env_var_or_default('NO_CACHE_TO', '')
prNum := env_var_or_default('prNum', '')

set shell := ["/bin/bash", "-c"]

@default:
    #!/bin/bash
    set -o xtrace
    echo **{{GITHUB_STEP_SUMMARY}}**


# Get a bash shell in the web container
shell:
    docker compose run --rm web bash

# Rebuild local development container
rebuild:
    docker compose rm -f web
    docker compose build --force-rm web

# display image layer names (e.g.: just build [name])
layers:
    @echo -en "\nDockerfile layers:\n\n"; sed -Ene '/^FROM/s/^FROM.*as (.*)$/\t\1/p' Dockerfile

version:
    @[[ -n "{{prNum}}" ]] && echo {{VERSION}}-{{prNum}} || echo {{VERSION}}

tag:
    @echo {{IMAGE_REGISTRY}}:$( just version )

registry:
    @echo {{IMAGE_REGISTRY}}

# Compile new python dependencies
# Taken from https://github.com/revsys/alphakit/blob/main/justfile
@pip-compile *ARGS:
    docker compose run \
        --entrypoint= \
        --rm web \
            bash -c "PIP_TOOLS_CACHE_DIR=/nuremberg/.cache/ pip-compile {{ ARGS }} ./requirements.in \
                --resolver=backtracking \
                --output-file ./requirements.txt"

# Upgrade existing Python dependencies to their latest versions
@pip-compile-upgrade:
    just pip-compile --upgrade


_test-packages:
  @tail -n  $( echo $(( $( wc -l web/requirements.in | cut -d" " -f1 ) - $( grep -nie '^#[[:blank:]]*test' web/requirements.in  | cut -d":" -f1) ))  ) web/requirements.in

##############################################################################
# NOTE: This is only for CI and should NOT be run in local development
##############################################################################
# build [step], tag it with {{IMAGE_REGISTRY}}:{{VERSION}}-{{step}} except for release target
build step='release' action='--load' verbosity='1':
    #!/usr/bin/env bash
    just buildkit-up

    if [[ "{{ step }}" == "release" ]];
    then
        endbits={{VERSION}}
        cendbits={{VERSION}}
    else
        [[ -n "{{prNum}}" ]] && step={{prNum}}-{{step}} || step={{step}}
        endbits={{VERSION}}-${step}
        cendbits=last-${step}
    fi

    [[ -n "{{verbosity}}" ]] && verbosity="--progress auto" || verbosity="--quiet"

    cache="--cache-from=type=registry,ref={{CACHE_REGISTRY}}:last --cache-from=type=registry,ref={{CACHE_REGISTRY}}:${cendbits}"
    [[ -z "{{NO_CACHE_TO}}" ]] && cache="${cache} --cache-to=type=registry,ref={{CACHE_REGISTRY}}:${cendbits},mode=max"

    echo "Building {{IMAGE_REGISTRY}}:${endbits}"
    set -o xtrace

    docker buildx build ${verbosity} ${cache} {{action}} --platform linux/amd64 -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} . ||
        docker buildx build --progress plain ${cache} {{action}} -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .

    just buildkit-down


# push image to registry
push step='release':
    #!/usr/bin/env bash
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    just build {{step}} --push

# execute new solr image build process
regen-solr-image nopush='':
    just solr-dc down -v >& /dev/null
    docker inspect $( just tag ) >& /dev/null || just build release --load ''
    just solr-dc up -d --quiet-pull solr-loader
    SOLR_NO_RESTORE=1 SOLR_BUILD=1 ./init.sh
    just solr-dc up -d --quiet-pull solr-data-load
    SOLR_RESTORE_SNAPSHOT= SOLR_DIST_DATA=1 SOLR_BUILD=1 ./init.sh || exit 1
    NO_CACHE_TO=1 just build solr || exit 1
    [[ -z "{{nopush}}" ]] && docker push $( just tag )-solr

# fs path to solr-image-build compose file
@solr-compose: _solr-compose
_solr-compose:
    @echo {{justfile_directory()}}/docker-compose.solr-build.yml

# shortcut for interacting w/ the solr image-build docker-compose project
@solr-dc *args='ps':
    docker compose -f $( just solr-compose ) -p solrbld {{args}}

# shortcut for interacting w/ the CI docker-compose project
@ci-dc *args='ps':
    docker compose -f ./docker-compose.yml -f ./docker-compose.ci.yml -p ci {{args}}

# target for running tests IN CI
test:
    #!/usr/bin/env bash
    export prNum= &&
    docker inspect $( just tag )-tester >& /dev/null || NO_CACHE_TO=1 just build tester --load '' &&
    just ci-dc up -d --quiet-pull &&
    just ci-dc exec -T -u0  web find /tmp /nuremberg /code -type f -not -user ${UID} -exec chown -Rv $UID {} +  | wc -l &&
    just ci-dc exec -T -e pytest_report_title="Code" -u$UID web pytest --verbose --github-report || exit 1
    # Browser tests are run but not accounted for failure since they are very brittle
    just ci-dc exec -T -e pytest_report_title="Selenium" -u$UID web pytest --verbose --github-report --no-cov nuremberg/documents/browser_tests.py || true

# executes bump2version on local repository (e.g.: just bump patch; just bump build)
@bump part='build' *args='':
    docker run -u ${UID} --rm -v $PWD:/code --workdir /code registry.revsys.com/bump2version {{part}} {{args}}


# updates last/{{env}}/deploy and {{env}}/deploy tags to trigger flux deployment
@deploy env='dev':
    git fetch --tags -f
    git tag -f last/{{env}}/deploy {{env}}/deploy
    git tag -f {{env}}/deploy {{VERSION}}
    git push --tags --force

@_make-bv:
    just build b2v
    docker tag $( just tag )-b2v registry.revsys.com/bump2version
    docker push registry.revsys.com/bump2version > /dev/null

@_make-just:
    just build just
    docker tag $( just tag )-just registry.revsys.com/just
    docker push registry.revsys.com/just

_drop-just:
    docker pull registry.revsys.com/just >& /dev/null || just _make-just
    docker run --user ${UID} --rm -v $PWD/.bin:/dist registry.revsys.com/just

# setup buildkit runner
@buildkit-up:
    #!/bin/bash
    set -o pipefail
    [[ -n $( docker buildx ls | grep 'default.*docker' ) ]] &&
        docker buildx create --platform linux/amd64 --bootstrap --name nuremberg-builder >& /dev/null
        docker buildx use nuremberg-builder

# take down buildkit runner & configure local docker for default builds
@buildkit-down:
    docker buildx use default
    docker buildx stop nuremberg-builder

# target that wraps simple strings with figlet(6) e.g.: just banner version
banner args='':
    #!/usr/bin/env bash
    docker inspect registry.revsys.com/bump2version >& /dev/null &&
        just _figlet $( just {{args}} ) ||
        ( docker pull registry.revsys.com/bump2version >& /dev/null || just _make-bv && just _figlet $( just {{args}} ) )

_figlet args='':
    #!/usr/bin/env bash
    docker run --entrypoint figlet --rm registry.revsys.com/bump2version -c -f standard -m0 -w117 {{args}}



update-local-tags:
    git fetch --tags --force


# update the latest SQLite DB dump with the provided MySQL's dump
update-db-dump mysqldump='' dump_name=`date --utc +%FT%T`:
    #!/usr/bin/env bash
    set -euxo pipefail
    # Convert the MySQL dump to SQLite format
    [[ -n "{{ mysqldump }}" ]] && mysql2sqlite/mysql2sqlite {{mysqldump}} | sqlite3 web/nuremberg_dev.db
    # Confirm no local users were created in the local DB
    [[ `sqlite3 web/nuremberg_dev.db 'SELECT COUNT(*) FROM auth_user;'` -eq 0 ]] || exit 1
    # Zip the DB and update the symlink to the latest dump
    zip -j -FS dumps/nuremberg_prod_dump_{{ dump_name }}.sqlite3.zip web/nuremberg_dev.db
    ln -fs nuremberg_prod_dump_{{ dump_name }}.sqlite3.zip dumps/nuremberg_prod_dump_latest.sqlite3.zip
    # ToDo: run commands such as update of author metadata or document images
    git add dumps/nuremberg_prod_dump_{{ dump_name }}.sqlite3.zip


# Rebuild the symlink to the latest dump to force Solr to rebuild
force-solr-regen:
    cd dumps
    git rm nuremberg_prod_dump_latest.sqlite3.zip
    ln -s nuremberg_prod_dump_2023-02-23T21:04:25.sqlite3.zip nuremberg_prod_dump_latest.sqlite3.zip
    git add nuremberg_prod_dump_latest.sqlite3.zip
