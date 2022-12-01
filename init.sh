#!/usr/bin/env bash

set -o xtrace 


SOLR_CORE="nuremberg_dev"
SOLR_HOME="/var/solr/data/$SOLR_CORE"
SOLR_SNAPSHOT_DIR=$PWD/dumps/nuremberg_solr_snapshot_latest
SOLR_URL="http://localhost:8983/solr"

if [[ -z ${SOLR_BUILD} ]];
then 
	solr=solr 
	web=web
	DOCKER_COMPOSE="docker-compose"
else
	solr=solr-data-load
	web=solr-loader
	DOCKER_COMPOSE="docker-compose -f $( just _solr-compose) -p solrbld"
fi

DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"

echo "Setting up sqlite"
install -vd $PWD/tmp -m 0777
unzip -o -d $PWD/tmp dumps/nuremberg_prod_dump_latest.sqlite3.zip 

$DOCKER_COMPOSE_EXEC ${web} cp -v /mnt/nuremberg_dev.db /tmp
$DOCKER_COMPOSE_EXEC ${web} ./manage.py migrate || exit 1


if [[ -z ${SOLR_NO_RESTORE} ]];
then
	echo "Wait for Solr to be ready..."
	while ! $DOCKER_COMPOSE_EXEC ${solr} solr status >/dev/null 2>&1; do
	    sleep 1
	done
	echo "Solr ready!!!"

	echo "Setting up solr config"

	$DOCKER_COMPOSE cp solr_conf/ ${solr}:/opt/solr-8.11.2/solr_conf
	$DOCKER_COMPOSE_EXEC ${solr} cp -r /opt/solr-8.11.2/solr_conf $SOLR_HOME

	http_code=$( $DOCKER_COMPOSE_EXEC ${solr} curl -sS -o /dev/null -w '%{http_code}' "$SOLR_URL/admin/cores?action=reload&core=$SOLR_CORE" ) || exit 1

	if [[ $http_code == 200 ]]; then
	    echo "Solr core already exists"
	else
	    echo "Solr core does not exist, creating it"
	    $DOCKER_COMPOSE_EXEC ${solr} solr create_core -c $SOLR_CORE -d /opt/solr-8.11.2/solr_conf || exit 1
	fi
	if [[ -n ${SOLR_RESTORE_SNAPSHOT} ]]; then
	    echo "Restoring Solr snapshot $SOLR_SNAPSHOT_DIR"
	    cat $SOLR_SNAPSHOT_DIR/* | $DOCKER_COMPOSE_EXEC ${solr} tar -xzv -f - --strip-component=1 -C $SOLR_HOME/data
	    $DOCKER_COMPOSE_EXEC -T ${solr} curl -sS "$SOLR_URL/$SOLR_CORE/replication?command=restore" || exit 1
	else
	    echo "Rebuilding Solr index (SLOW)"
	    time $DOCKER_COMPOSE_EXEC ${web} python manage.py rebuild_index -k8 -b500 --noinput || exit 1
	fi
fi

[[ -n ${SOLR_DIST_DATA} ]] && \
	sleep 10 && \
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} tar --sparse -cz -f /dist/var-solr.tgz /var/solr && \
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} chown -Rv $UID /dist


