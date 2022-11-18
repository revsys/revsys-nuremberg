#vim: ft=make ts=4 sw=4 et
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
