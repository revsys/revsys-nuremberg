import re

from django.db import transaction
from django.db.models import F, Func, OuterRef, Subquery, Value
from django.db.models.functions import Concat, Trim
from django.core.management.base import BaseCommand

from nuremberg.documents.models import (
    DocumentImage,
    OldDocumentImage,
)


class DryRunRequested(Exception):
    """Do not make changes to the db when --dry-run was requested."""

    def __init__(self, created, updated, *args, **kwargs):
        self.created = created
        self.updated = updated
        super().__init__(*args, **kwargs)


class Command(BaseCommand):
    help = 'Backfill/update DocumentImages for any missing/updated images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            default=None,
            help='Document IDs to be processed (default is all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=(
                'Calculate how many items would be back filled but make no '
                'actual changes'
            ),
        )

    def debug(self, title, content):
        self.stdout.write(f'\n*** DEBUG: {title} ***\n\n')
        self.stdout.write(content or '<Empty>')
        self.stdout.write('\n\n\n')

    def create_images(self, document_ids=None):
        existing_images = DocumentImage.objects.filter(
            document_id=OuterRef('document_id')
        )
        missing = (
            OldDocumentImage.objects.exclude(
                page_number__in=Subquery(existing_images.values('page_number'))
            )
            .select_related('image_type')
            .order_by('document_id', 'page_number')
        )
        if document_ids:
            missing = missing.filter(document_id__in=document_ids)

        to_create = []
        for old_image in missing:
            image = DocumentImage(
                document_id=old_image.document_id,
                page_number=old_image.page_number,
                image=old_image.filename,
                image_type=old_image.image_type,
                scale=DocumentImage.SCREEN,
            )
            if old_image.physical_page_number:
                physical_page_number = re.sub(
                    r'[^\d]', '', old_image.physical_page_number
                )
                if physical_page_number:
                    image.physical_page_number = int(physical_page_number)
            to_create.append(image)

        assert len(to_create) == missing.count(), (
            f'Instances to be created ({len(to_create)}) do not match count '
            f'in DB ({missing.count()})'
        )
        created = DocumentImage.objects.bulk_create(to_create)
        self.debug(
            'Created DocumentImages', '\n'.join(str(i) for i in created)
        )
        return len(created)

    def update_images(self, document_ids=None):
        # There are entries in tblImagesList with FileName ending in `\r`
        source_of_truth = OldDocumentImage.objects.annotate(
            filename_with_ext=Concat(
                Trim(Func(F('base_filename'), Value('\r'), function='TRIM')),
                Value('.'),
                Trim(Func(F('fileformat'), Value('\r'), function='TRIM')),
            )
        ).filter(
            document_id=OuterRef('document_id'),
            page_number=OuterRef('page_number'),
        )
        outdated = (
            DocumentImage.objects.annotate(
                new_filename=Subquery(
                    source_of_truth.values('filename_with_ext')[:1]
                )
            )
            .exclude(
                image=F('new_filename'),
            )
            .order_by('document_id', 'page_number')
        )
        if document_ids:
            outdated = outdated.filter(document_id__in=document_ids)

        self.debug(
            'Outdated DocumentImages',
            '\n'.join(
                f'#{i.document_id} p.{i.page_number} -- '
                f'update {i.image!r} --> {i.new_filename!r}'
                for i in outdated
            ),
        )

        updated = outdated.update(
            image=Subquery(source_of_truth.values('filename_with_ext'))
        )
        return updated

    @transaction.atomic
    def backfill(self, document_ids=None, dry_run=False):
        updated = self.update_images(document_ids)
        created = self.create_images(document_ids)
        from django.db import connection

        self.debug(
            'DB Queries',
            '\t' + '\n\n\t'.join(repr(q['sql']) for q in connection.queries),
        )

        if dry_run:
            raise DryRunRequested(created=created, updated=updated)

        return created, updated

    def handle(self, *args, **options):
        self.stdout.write(f'Starting backfill for images ({options=})')

        model_name = DocumentImage.__name__
        try:
            created, updated = self.backfill(
                document_ids=options['ids'],
                dry_run=options['dry_run'],
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
