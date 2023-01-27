#!/usr/bin/env bash
# vim: shiftwidth=4 tabstop=4 filetype=bash noexpandtab list

set -o pipefail

SOLR_CORE="nuremberg_dev"
SOLR_HOME="/var/solr/data/$SOLR_CORE"
SOLR_HOST="http://localhost:8983"
SOLR_URL="$SOLR_HOST/solr"
SOLR_CORE_STATUS="$SOLR_URL/admin/cores?action=STATUS"

if [[ -z ${SOLR_BUILD} ]];
then
	solr=solr
	web=web
	DOCKER_COMPOSE="${DOCKER_COMPOSE:-docker-compose}"
else
	solr=solr-data-load
	web=solr-loader
	DOCKER_COMPOSE="just solr-dc "
fi

DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"

echo "Setting up sqlite"

# the compressed database file is already a part of the release and tester images.
if [[ -z "${SOLR_BUILD}" ]] ;
then
	$DOCKER_COMPOSE cp -L dumps/nuremberg_prod_dump_latest.sqlite3.zip ${web}:/tmp/ || exit 1
	$DOCKER_COMPOSE_EXEC --user 0 ${web} chown ${UID} /tmp/*zip
	$DOCKER_COMPOSE_EXEC --user $UID ${web} python -m zipfile -e /tmp/nuremberg_prod_dump_latest.sqlite3.zip /nuremberg/
else
	$DOCKER_COMPOSE_EXEC --user $UID ${web} python -m zipfile -e /code/data/nuremberg_prod_dump_latest.sqlite3.zip /nuremberg/
fi

$DOCKER_COMPOSE_EXEC --user ${UID} ${web} ./manage.py makemigrations -v1
$DOCKER_COMPOSE_EXEC --user ${UID} ${web} ./manage.py migrate -v1


# the solr image used for deployments & CI already carries its data
if [[ -z ${SOLR_NO_RESTORE} ]];
then
	echo "Wait for Solr to be ready..."
	while ! $DOCKER_COMPOSE_EXEC ${solr} solr status >/dev/null 2>&1; do
		echo -en '.'
		sleep 1
	done
	echo
	echo "Solr ready!!!"

	echo "Setting up solr config"
	$DOCKER_COMPOSE cp solr_conf ${solr}:/opt/solr-8.11.2/ && \
	$DOCKER_COMPOSE_EXEC -u0 ${solr} cp -Rp /opt/solr-8.11.2/solr_conf /var/solr/data/nuremberg_dev && \
	$DOCKER_COMPOSE_EXEC -u0 ${solr} chown -R solr:solr /var/solr/data solr_conf || exit 1
	$DOCKER_COMPOSE_EXEC ${solr} solr create_core -c $SOLR_CORE -d solr_conf || echo 'Solr core already exists'

	echo "Rebuilding Solr index (SLOW)"
	time $DOCKER_COMPOSE_EXEC ${web} python manage.py rebuild_index -b500 -k4 --noinput || exit 1
fi

# this is used by the regen-solr-image just(1) target
if [[ -n ${SOLR_DIST_DATA} ]];
then
	sleep 20
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} sync
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} tar --sparse -cz -f /dist/var-solr.tgz /var/solr
	$DOCKER_COMPOSE_EXEC -u 0 -T ${solr} chown -Rv $UID /dist
fi
