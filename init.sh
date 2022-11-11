#!/usr/bin/env bash

set -xe

DOCKER_COMPOSE="docker compose"
DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"
SOLR_CORE="nuremberg_dev"
SOLR_HOME="/var/solr/data/$SOLR_CORE"
SOLR_SNAPSHOT_DIR="dumps/nuremberg_solr_snapshot_latest"
SOLR_SNAPSHOT_NAME="221115"
SOLR_URL="http://localhost:8983/solr"

echo "Setting up sqlite"
unzip -p dumps/nuremberg_prod_dump_latest.sqlite3.zip > web/nuremberg_dev.db

echo "Wait for Solr to be ready..."
while ! $DOCKER_COMPOSE_EXEC solr solr status >/dev/null 2>&1; do
    sleep 1
done
echo "Solr ready!!!"

echo "Setting up solr config"
$DOCKER_COMPOSE cp solr_conf/ solr:/opt/solr-8.11.2/solr_conf
$DOCKER_COMPOSE_EXEC solr cp -r /opt/solr-8.11.2/solr_conf $SOLR_HOME

http_code=`curl -sS -o /dev/null -w '%{http_code}' "$SOLR_URL/admin/cores?action=reload&core=$SOLR_CORE"`
if [[ $http_code == 200 ]]; then
    echo "Solr core already exists"
else
    echo "Solr core does not exist, creating it"
    $DOCKER_COMPOSE_EXEC solr solr create_core -c $SOLR_CORE -d solr_conf
fi

if [[ -z ${SOLR_RESTORE_SNAPSHOPT} ]]; then
    echo "Rebuilding Solr index (SLOW)"
    $DOCKER_COMPOSE_EXEC web python manage.py rebuild_index --noinput
else
    echo "Restoring Solr snapshot from $SOLR_SNAPSHOT_DIR"
    cat $SOLR_SNAPSHOT_DIR/* | $DOCKER_COMPOSE_EXEC solr tar xzvf - -C $SOLR_HOME/data
    $DOCKER_COMPOSE_EXEC solr curl -sS "$SOLR_URL/$SOLR_CORE/replication?command=restore&name=$SOLR_SNAPSHOT_NAME"
    sleep 3
    $DOCKER_COMPOSE_EXEC solr curl http://localhost:8983/solr/nuremberg_dev/replication?command=details
fi
