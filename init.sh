#!/usr/bin/env bash

set -xe

DOCKER_COMPOSE="docker compose"
DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"

echo "Setting up sqlite"
cp dumps/nuremberg_prod_dump_2022-08-02.sqlite3.zip . && unzip nuremberg_prod_dump_2022-08-02.sqlite3
mv nuremberg_prod_dump_2022-08-02.sqlite3 web/nuremberg_dev.db

echo "Migrating databases"
$DOCKER_COMPOSE_EXEC web python manage.py migrate

echo "Setting up solr index (slow)"
$DOCKER_COMPOSE cp solr_conf/ solr:/opt/solr-8.11.2/solr_conf
$DOCKER_COMPOSE_EXEC solr cp -r /opt/solr-8.11.2/solr_conf /var/solr/data/nuremberg_dev
$DOCKER_COMPOSE_EXEC solr solr create_core -c nuremberg_dev -d solr_conf
$DOCKER_COMPOSE_EXEC web python manage.py rebuild_index --noinput
