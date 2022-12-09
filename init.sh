#!/usr/bin/env bash
# vim: shiftwidth=4 tabstop=4 filetype=bash noexpandtab list

SOLR_CORE="nuremberg_dev"
SOLR_HOME="/var/solr/data/$SOLR_CORE"
SOLR_SNAPSHOT_DIR=$PWD/dumps/nuremberg_solr_snapshot_latest
SOLR_URL="http://localhost:8983/solr"

if [[ -z ${SOLR_BUILD} ]];
then
	solr=solr
	web=web
	DOCKER_COMPOSE="${DOCKER_COMPOSE:-docker-compose}" 
else
	solr=solr-data-load
	web=solr-loader
	DOCKER_COMPOSE="docker-compose -f $( just _solr-compose) -p solrbld"
fi

DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"

echo "Setting up sqlite"

# the compressed database file is already a part of the release and tester images. 
if [[ -z "${SOLR_BUILD}" ]] ;
then
	docker compose cp -L dumps/nuremberg_prod_dump_latest.sqlite3.zip web:/tmp/
	$DOCKER_COMPOSE_EXEC ${web} python -m zipfile -e /tmp/nuremberg_prod_dump_latest.sqlite3.zip /nuremberg/
else
	$DOCKER_COMPOSE_EXEC ${web} python -m zipfile -e /code/data/nuremberg_prod_dump_latest.sqlite3.zip /tmp
fi

$DOCKER_COMPOSE_EXEC ${web} ./manage.py makemigrations -v1
$DOCKER_COMPOSE_EXEC ${web} ./manage.py migrate -v1


# the solr image used for deployments & CI already carries its data
if [[ -z ${SOLR_NO_RESTORE} ]];
then
	echo "Wait for Solr to be ready..."
	while ! $DOCKER_COMPOSE_EXEC ${solr} solr status >/dev/null 2>&1; do
		/bin/echo -en '.'
		sleep 1
	done
	echo
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

# this is used by the regen-solr-image just(1) target
if [[ -n ${SOLR_DIST_DATA} ]];
then
	sleep 10
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} tar --sparse -cz -f /dist/var-solr.tgz /var/solr
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} chown -Rv $UID /dist
fi
