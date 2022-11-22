#vim: ft=just ts=4 sw=4 et
set dotenv-load := false
IMAGE_REGISTRY := 'registry.revsys.com/nuremberg'
VERSION := 'v0.2.3'


list:
    just --list

# rebuild requirements files
requirements:
  #!/usr/bin/env bash
  pushd web
  pip-compile web/requirements.in -o web/requirements.txt &&
  pip-compile <( head -n$( grep -n "# Dev" web/requirements.in | cut -d":" -f1 ) web/requirements.in  ) -o web/requirements.prod.txt
  popd

_build step='release':
    #!/usr/bin/env bash
    echo "step={{ step }}"
    [[ "{{ step }}" == "release" ]] && endbits={{VERSION}} || endbits={{VERSION}}-{{ step }}
    docker buildx build -t  {{IMAGE_REGISTRY}}:${endbits} --target {{step}} .

make-release-image: (_build "release")

push-release-image: (_build "release")
    #!/usr/bin/env bash
    docker push {{IMAGE_REGISTRY}}:{{VERSION}}

deploy:
    @helm upgrade -i hlsnp --namespace nuremberg chart/

gensolr:
    #!/usr/bin/env bash
    set -o xtrace verbose
    rm -rf /tmp/solr_data; mkdir /tmp/solr_data
    sed -iEe '/var\/solr/s/solr_data/\/tmp\/solr_data/' docker-compose.yml;
    docker-compose up -d --force-recreate solr
    docker-compose up -d --force-recreate web
    #git checkout docker-compose.yml
