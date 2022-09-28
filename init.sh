#!/usr/bin/env bash

set -xe

DOCKER_COMPOSE="docker compose"
DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"
SOLR_CORE="nuremberg_dev"
SOLR_HOME="/var/solr/data/$SOLR_CORE"
SOLR_SNAPSHOT_NAME="nuremberg_solr_snapshot_2022-09-28.tar.gz"
SOLR_URL="http://localhost:8983/solr"

echo "Setting up sqlite"
cp dumps/nuremberg_prod_dump_2022-08-02.sqlite3.zip . && unzip nuremberg_prod_dump_2022-08-02.sqlite3
mv nuremberg_prod_dump_2022-08-02.sqlite3 web/nuremberg_dev.db

echo "Migrating databases"
$DOCKER_COMPOSE_EXEC web python manage.py migrate

echo "Setting up solr index (slow)"
$DOCKER_COMPOSE cp solr_conf/ solr:/opt/solr-8.11.2/solr_conf
$DOCKER_COMPOSE_EXEC solr cp -r /opt/solr-8.11.2/solr_conf $SOLR_HOME

$DOCKER_COMPOSE_EXEC solr solr status
sleep 5
$DOCKER_COMPOSE_EXEC solr solr status

http_code=`curl -sS -o /dev/null -w '%{http_code}' "$SOLR_URL/admin/cores?action=reload&core=$SOLR_CORE"`
if [[ $http_code == 200 ]]
then
    echo "Solr core already exists"
else
    echo "Solr core does not exist, creating it"
    $DOCKER_COMPOSE_EXEC solr solr create_core -c $SOLR_CORE -d solr_conf
fi
$DOCKER_COMPOSE cp dumps/$SOLR_SNAPSHOT_NAME solr:$SOLR_HOME/data
$DOCKER_COMPOSE_EXEC solr tar xzvf $SOLR_HOME/data/$SOLR_SNAPSHOT_NAME -C $SOLR_HOME/data
$DOCKER_COMPOSE_EXEC solr curl -sS "$SOLR_URL/$SOLR_CORE/replication?command=restore"
# $DOCKER_COMPOSE_EXEC web python manage.py rebuild_index --noinput
