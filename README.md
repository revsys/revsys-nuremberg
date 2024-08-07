# HLS Nuremberg Trials Project


> This is a Django web site for the digital archives of the Nuremberg Trials
> Project maintained by the Harvard Law Library.  It is intended as a
> open-access web app for scholars, researchers, and members of the public,
> exposing the digitized documents, full-text trial transcripts, and rich
> search features for the same in a friendly, modern interface.


## Setup

The client uses [Docker/Docker Compose](https://docs.docker.com/compose/). In
the host computer, run:

```shell
docker compose up
```

Populate the database and the search engine index (this could take some time):

```shell
./init.sh
```

Then visit [localhost:8000](http://localhost:8000).

To run with production settings, set appropriate `SECRET_KEY`,
`ALLOWED_HOSTS`, and `HOST_NAME` env vars, and run:

```shell
docker compose up -d
docker compose exec web python manage.py compress
docker compose exec web python manage.py collectstatic
```

Then visit [localhost:8080](http://localhost:8080).
(If you get a 502 wait a few seconds and then refresh the page.)

When you are finished,

```shell
docker compose down
```

## Project Structure

The project is organized into several feature-oriented modules ("apps" in
Django parlance). Each module includes all URL routing, model and view code,
tests, templates, JavaScript code, and static assets for the corresponding
feature set:

- `nuremberg`: Top-level namespace for organizational purposes only.
- `.core`: Top-level URL routing, test frameworks, base templates and
middleware, and site-wide style files.
- `.settings`: Environment-specific Django settings files.
- `.content`: Files for static pages with project information, etc.
- `.documents`: Files for displaying digitized document images.
- `.transcripts`: Files for full-text transcripts and OCR documents.
- `.photographs`: Files for displaying images from the photographic archive.
- `.search`: Files for the search interface and API.

## Testing

Tests in the project are generally high-level integration acceptance tests that
exercise the full app stack in a deployed configuration. Since the app has the
luxury of running off of a largely static dataset, the test database is
persistent, greatly speeding up setup and teardown time.

### Running tests

Make sure you have initialized the database and solr index as described in
[Setup](#setup) above. Then run:

```shell
docker compose exec web pytest
```

Pytest is configured in `pytest.ini` to run all files named `tests.py`.

There is also a Selenium suite to test the behavior of the document viewer front end. These tests take a while to run, don't produce coverage data, and
are relatively unreliable, so they aren't run as part of the default suite.
However, they are still useful, as they exercise the full stack all the way
through image downloading and preloading. They can be run explicitly when
necessary.

```shell
docker compose exec web pytest nuremberg/documents/browser_tests.py
```


## Project Settings

The Django settings live in the `nuremberg/settings.py`.

Secrets (usernames, passwords, security tokens, nonces, etc.) should not be
placed in a settings file or committed into git. The proper place for these is
an environment variable configured on the host and read via `os.environ`.

## Data

Since it is expected that this app will host a largely static dataset, the
Django admin is enabled purely in read-only mode. Updates can be made directly
in SQLite. Just ensure that any changes are reindexed by Solr.

An admin interface is provided via the usual `/admin` URL. For it to be
operable, you will need to use the Django management command to create an admin
user for your use. If you choose to do so, make sure not to commit and deploy your changes!


### Updating the database dump in the repo

In order to update the database dump included in the repo, first of all, every
local user should be removed. To do so open a python shell using
`docker compose run --rm web python manage.py shell` and then run:

```shell
>>> from django.contrib.auth import get_user_model
>>> get_user_model().objects.all().delete()
(0, {})
>>>
```

Some of the data for this project is taken from external MySQL/MariaDB SQL
dumps. To import a SQL dump named `some-table.sql`, follow these steps:

1. Ensure you have the [just](https://github.com/casey/just) CLI tool available

2. Invoke the db dump updater command:

```shell
just update-db-dump some-table.sql
```

> **_NOTE:_** The mysql2sqlite converter's README says: *both mysql2sqlite and
> sqlite3 might write something to stdout and stderr - e.g. memory coming
> from PRAGMA journal_mode = MEMORY; is not harmful*.

Review the changes and potentially:

 1. Confirm that the symlink `dumps/nuremberg_prod_dump_latest.sqlite3.zip` is
 pointing to a valid zipfile:

```shell
ls -la `realpath dumps/nuremberg_prod_dump_latest.sqlite3.zip`
```

 2. Remove older dump(s)
 3. Stage and commit your changes to the git repo


### Backfill/Update of author metadata

If the DB dump update would include changes to the
`tblNurAuthorsWikidataPropertiesAndQualifiers` table, then the model
`DocumentAuthorExtra` instances need update. To do so, use the following
management command (check the help options for further information):

```shell
docker compose exec web python manage.py backfill_author_metadata --help
```


### Backfill/Update of document images

If the DB dump update would include changes to the `tblImagesList` table, then
the model `DocumentImage` instances need update or creation for new entries.
To do so, use the following management command (check the help options for
further information):

```shell
docker compose exec web python manage.py backfill_document_images --help
```

It is recommended to first do a dry run with this command:

```shell
docker compose exec web python manage.py backfill_document_images --dry-run
```

and then after result output inspection, do an actual run by removing the
`--dry-run` switch.


## Solr

Solr indexes are defined in relevant `search_indexes.py` files, and additional
indexing configuration is in the
`search/templates/search_configuration/schema.xml` file used to generate
`solr_conf/schema.xml`.

### Starting fresh

To build a brand new Solr schema, run:

```shell
docker compose run --rm web python manage.py build_solr_schema --configure-dir=solr_conf
```

This will generate both `schema.xml` and `solrconfig.xml` under the `solr_conf`
directory. To use the updated config files, run `docker compose down -v` to dispose
of the existing solr container and `docker compose up -d` to start a fresh one.

### Reindexing

To rebuild the index contents, run:

```
docker compose run --rm web python manage.py rebuild_index
```

(It will take a couple of minutes to reindex fully.)

Do this any time you make changes to `search_indexes.py` or `schema.xml`.

In the past, when this site was under active development and more frequent
reindexing was required, `manage.py update_index` was run via a `cron` script or
similar to automate reindexing on a nightly or hourly basis using `--age 24` or
`--age 1`. (Note: This will restrict reindexing only for indexes that have an
`updated_at` field defined; currently, `photographs` does not, but completely
reindexing that model is fast anyway.)

For more fine-grained information on indexing progress, use `--batch-size 100
--verbosity 2` or similar.

### Deploying

The Solr schema must be maintained as part of the deploy process. When
deploying an updated schema, make sure you have generated and committed
new `schema.xml` and `solrconfig.xml` files using `manage.py build_solr_schema
--configure-dir=solr_conf`, and then run a complete reindexing.


## Transcripts

There is a management command `manage.py ingest_transcript_xml` which reads a
file like `NRMB-NMT01-23_00512_0.xml` (or a directory of such files using `-d`)
and generates or updates the appropriate transcript, volume, and page models.
Since some values read out of the XML are stored in the database, re-ingesting
is the preferred way to update transcript data. If database XML is modified
directly, call `populate_from_xml` on the appropriate TranscriptPage model to
update date, page, and sequence number.

Remember to run `docker compose exec web python manage.py update_index transcripts` after ingesting XML to
enable searching of the new content.


## Static Assets

### CSS

CSS code is generated from `.less` files that live in
`nuremberg/core/static/styles`. The styles are built based on Bootstrap 3
mixins, but don't bundle any Bootstrap code directly to ensure a clean semantic
design.

Compilation is handled automatically by the `django-static-precompiler` module
while the development server is running.

### JavaScript

JavaScript code is organized simply. JS dependencies are in
`core/static/scripts`, and are simply included in `base.html`. App code is
modularized using `modulejs`, to ensure that only code in the module defined in
the relevant template is run.

The only significant JavaScript app is the document image loading, panning, and
zooming functionality implemented in `documents/scripts`. That functionality is
organized as a set of Backbone.js views and viewmodels. There is a smaller
amount of code in `transcripts` to handle infinite scrolling and page
navigation, which is implemented in pure jQuery. There are also a handful of
minor cosmetic features implemented in `search`.

In production, all site javascript is compacted into a single minified blob by
`compressor`. (The exception is the rarely-needed dependency `jsPDF`.)

