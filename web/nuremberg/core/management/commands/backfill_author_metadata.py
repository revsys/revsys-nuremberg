from io import BytesIO

import requests
from django.db import transaction
from django.core.management.base import BaseCommand

from nuremberg.core.storages import AuthorStorage
from nuremberg.documents.models import (
    DocumentAuthorExtra,
    DocumentPersonalAuthor,
)


class DryRunRequested(Exception):
    """Do not make changes to the db when --dry-run was requested."""

    def __init__(self, created, updated, *args, **kwargs):
        self.created = created
        self.updated = updated
        super().__init__(*args, **kwargs)


class Command(BaseCommand):
    help = "Backfill author metadata based on existing properties/qualifiers"

    def add_arguments(self, parser):
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            default=None,
            help='Author IDs to process (default is all)',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Ensure that the links in properties are valid',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-download the image/links even if already available',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=(
                'Calculate how many authors would be back filled but make no '
                'actual changes'
            ),
        )

    def do_request(self, url, method='GET', **kwargs):
        kwargs.setdefault('headers', {'User-Agent': 'Ubuntu; Linux x86_64'})
        kwargs.setdefault('allow_redirects', True)
        response = getattr(requests, method.lower())(url, **kwargs)
        if not response.ok:
            self.stderr.write(
                f'Response is not OK, got {response.status_code=}, '
                f'{response.headers=}'
            )
        return response

    def download_and_store_image(self, image_url, image_path, force=False):
        self.stdout.write(
            f'Downloading {image_url=} into {image_path=} ({force=})'
        )
        response = self.do_request(image_url)
        if not response.ok:
            return

        media_storage = AuthorStorage()
        bucket_name = getattr(media_storage, 'bucket_name', 'local FS')

        if force or not media_storage.exists(image_path):
            media_storage.save(image_path, BytesIO(response.content))
            file_url = media_storage.url(image_path)
            self.stdout.write(
                f'Saved {image_path=} in {bucket_name=} with {file_url=}'
            )
        else:
            self.stderr.write(
                f'Can not save {image_path=} in {bucket_name=} because the '
                f'path already exists (and `force` was unset).'
            )

    def process_image(self, metadata, dry_run, force):
        image_path = None
        image_alt = ''

        if metadata['image'] is None:
            return image_path, image_alt

        image_url = metadata['image'].get('url')
        self.stdout.write(f'About to download {image_url=}')

        image_head = self.do_request(image_url, method='HEAD')
        size = image_head.headers.get('content-length')
        content_type = image_head.headers.get('content-type')
        if not content_type.startswith('image/'):
            self.stderr.write(
                f'Response is not an image, got {image_head.headers=}'
            )
            return image_path, image_alt

        image_suffix = content_type.replace('image/', '')
        image_path = (
            f'{metadata["author"]["id"]}-{metadata["author"]["slug"]}.'
            f'{image_suffix}'
        )

        image_alt = metadata['image'].get('alt')
        if dry_run:
            self.stdout.write(
                f'Would download {size=} bytes with {content_type=} from '
                f'{image_head.url=} (but dry-run was requested!)'
            )
            return image_path, image_alt

        self.download_and_store_image(image_url, image_path, force)

        return image_path, image_alt

    @transaction.atomic
    def backfill(self, qs, dry_run=False, force=False, check=False):
        # Create missing entries
        extra = []
        create_qs = qs.filter(extra__isnull=True)
        for metadata in create_qs.metadata():
            self.stdout.write(
                f'Creating extra instance for author {metadata["author"]=}'
            )
            image_path, image_alt = self.process_image(
                metadata, dry_run, force
            )
            p = DocumentAuthorExtra(
                author_id=metadata['author']['id'],
                description=metadata['author']['description'],
                image=image_path,
                image_alt=image_alt,
                properties=metadata['properties'],
            )
            extra.append(p)

        created = len(DocumentAuthorExtra.objects.bulk_create(extra))

        # Update existing entries if requested
        extra = []
        update_qs = qs.none()
        if force:
            update_qs = qs.filter(extra__isnull=False).select_related('extra')

        for author in update_qs:
            metadata = author.metadata()
            self.stdout.write(f'Updating extra instance for author {author=}')
            image_path, image_alt = self.process_image(
                metadata, dry_run, force
            )
            author.extra.description = metadata['author']['description']
            author.extra.image = image_path
            author.extra.image_alt = image_alt
            author.extra.properties = metadata['properties']
            extra.append(author.extra)

        updated = DocumentAuthorExtra.objects.bulk_update(
            extra, fields=['description', 'image', 'image_alt', 'properties']
        )

        # if check:
        #     for item in qs.model.objects.filter(id__in=[i.id for i in qs]):
        #         if item.image.url.startswith('/'):
        #             self.stderr.write(
        #                 f'Can not validate non absolute URL {item.image.url}.'
        #             )
        #             continue
        #         response = self.do_request(item.image.url, method='HEAD')
        #         if not response.ok:
        #             self.stderr.write(
        #                 f'Image URL at {item.image.url} returned HTTP Code '
        #                 f'{response.status_code}.'
        #             )

        if dry_run:
            raise DryRunRequested(created=created, updated=updated)

        return created, updated

    def handle(self, *args, **options):
        qs = DocumentPersonalAuthor.objects.all()
        model_name = qs.model.__name__
        if options['ids']:
            qs = qs.filter(id__in=options['ids'])
        if not qs:
            self.stderr.write(f'No {model_name} instances to be processed.')
            return

        self.stdout.write(f'Starting backfill for authors ({options=})')

        try:
            created, updated = self.backfill(
                qs=qs,
                dry_run=options['dry_run'],
                force=options['force'],
                check=options['check'],
            )
        except DryRunRequested as e:
            self.stdout.write(
                f'Would have created {e.created} and updated {e.updated} '
                f'{model_name}(s).'
            )
        else:
            self.stdout.write(
                f'Created {created} and updated {updated} {model_name}(s).'
            )
