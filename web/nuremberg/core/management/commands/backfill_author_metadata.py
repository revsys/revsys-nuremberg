from django.db import transaction
from django.core.management.base import BaseCommand

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

    @transaction.atomic
    def backfill(self, qs, dry_run=False, force=False):
        # First update existing entries if requested with force=True
        update_qs = qs.none()
        if force:
            update_qs = qs.filter(extra__isnull=False)
        self.stdout.write(
            f'Updating {len(update_qs)} DocumentAuthorExtra instance(s).'
        )
        updated = DocumentAuthorExtra.objects.bulk_update_from_author_qs(
            update_qs, dry_run, force
        )

        # Then, create missing DocumentAuthorExtra entries
        create_qs = qs.filter(extra__isnull=True)
        self.stdout.write(
            f'Creating {len(create_qs)} DocumentAuthorExtra instance(s).'
        )
        created = len(
            DocumentAuthorExtra.objects.bulk_create_from_author_qs(
                create_qs, dry_run, force
            )
        )

        if dry_run:
            raise DryRunRequested(created=created, updated=updated)

        return created, updated

    def handle(self, *args, **options):
        self.stdout.write(f'Starting backfill for authors ({options=})')

        qs = DocumentPersonalAuthor.objects.all()
        model_name = qs.model.__name__
        if options['ids']:
            qs = qs.filter(id__in=options['ids'])
        if not qs:
            self.stderr.write(f'No {model_name} instances to be processed.')
            return

        try:
            created, updated = self.backfill(
                qs=qs,
                dry_run=options['dry_run'],
                force=options['force'],
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
