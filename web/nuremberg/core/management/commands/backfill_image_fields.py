import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Q, Value
from django.db.models.functions import StrIndex, Substr

from nuremberg.documents.models import DocumentImage
from nuremberg.transcripts.models import TranscriptPage


class DryRunRequested(Exception):
    """Do not make changes to the db when --dry-run was requested."""

    def __init__(self, updated, *args, **kwargs):
        self.updated = updated
        super().__init__(*args, **kwargs)


class Command(BaseCommand):
    help = "Backfill ImageField's path based on existing url/image_url values"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--documents',
            action='store_true',
            help='Check document and their images',
        )
        group.add_argument(
            '--transcripts',
            action='store_true',
            help='Check transcripts and their pages',
        )
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            default=None,
            help='IDs to scan for missing images (default is all)',
        )
        parser.add_argument(
            '--prefix',
            type=str,
            required=True,
            help=(
                'Image filename prefix to be used to detect the right portion '
                'in the deprecated URLs fields'
            ),
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Ensure that the resulting image URL is a 200',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-populate the image even if already set in the instance',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=(
                'Calculate how many images would be back filled but make no '
                'actual changes'
            ),
        )

    @transaction.atomic
    def _backfill_images(
        self,
        qs,
        source_field,
        prefix,
        check=False,
        dry_run=False,
    ):
        updated = (
            qs.annotate(url_from_index=StrIndex(source_field, Value(prefix)))
            .filter(
                url_from_index__gt=0,
            )
            .update(
                image=Substr(source_field, F('url_from_index'), length=None),
            )
        )
        if check:
            for item in qs.model.objects.filter(id__in=[i.id for i in qs]):
                if item.image.url.startswith('/'):
                    self.stderr.write(
                        f'Can not validate non absolute URL {item.image.url}.'
                    )
                    continue
                response = requests.head(item.image.url)
                if not response.ok:
                    self.stderr.write(
                        f'Image URL at {item.image.url} returned HTTP Code '
                        f'{response.status_code}.'
                    )

        if dry_run:
            raise DryRunRequested(updated=updated)

        return updated

    def backfill_images(self, qs, prefix, dry_run, force, check):
        model_name = qs.model.__name__
        qs = qs.filter(_url__isnull=False)
        if not force:
            qs = qs.filter(Q(image__isnull=True) | Q(image=''))
        if not qs:
            self.stderr.write(f'No {model_name} to be processed.')
            return

        # XXX maybe do batch updates using filtered document IDs
        try:
            updated = self._backfill_images(
                qs,
                source_field='_url',
                prefix=f'{prefix}',
                check=check,
                dry_run=dry_run,
            )
        except DryRunRequested as e:
            self.stdout.write(
                f'Would have back filled {e.updated} {model_name}(s).'
            )
        else:
            self.stdout.write(f'Updated {updated} {model_name}(s).')

    def handle(self, *args, **options):
        if options['documents']:
            qs = DocumentImage.objects.all()
            if options['ids']:
                qs = qs.filter(document_id__in=options['ids'])
        elif options['transcripts']:
            qs = TranscriptPage.objects.all()
            if options['ids']:
                qs = qs.filter(transcript_id__in=options['ids'])
        else:
            # argparse's mutually exclusive group ensures we never reach this
            return

        self.backfill_images(
            qs=qs,
            prefix=options['prefix'],
            dry_run=options['dry_run'],
            force=options['force'],
            check=options['check'],
        )
