import logging
import operator
from collections import defaultdict

from django.db import models
from django.db.models import Case, Count, Subquery, Value, When
from django.db.models.functions import Concat
from django.utils.functional import cached_property
from django.utils.text import slugify

from nuremberg.core.storages import AuthorStorage, DocumentStorage
from nuremberg.documents.helpers import (
    build_image_path,
    download_and_store_image,
    parse_date,
)


logger = logging.getLogger(__name__)


class Document(models.Model):
    id = models.AutoField(primary_key=True, db_column='DocID')
    title = models.CharField(max_length=255, db_column='TitleDescriptive')
    literal_title = models.TextField(db_column='Title')
    description = models.TextField(db_column='Description')
    updated_at = models.DateTimeField(auto_now=True, db_column='Updated')

    image_count = models.IntegerField(db_column='NoOfImages', default=0)

    language = models.ForeignKey(
        'DocumentLanguage', db_column='DocLanguageID', on_delete=models.PROTECT
    )
    source = models.ForeignKey(
        'DocumentSource', db_column='DocVersionID', on_delete=models.PROTECT
    )

    class Meta:
        managed = False
        db_table = 'tblDoc'

    def __str__(self):
        return "#{0} - {1}".format(self.id, self.title)

    @cached_property
    def full_text(self):
        return self.full_texts().first()

    @cached_property
    def language_name(self):
        return self.language.name

    @cached_property
    def source_name(self):
        return self.source.name

    @cached_property
    def text(self):
        return self.full_text.text if self.full_text is not None else ''

    @cached_property
    def total_pages(self):
        return self.image_count

    def page_range(self):
        return range(1, (self.image_count or 0) + 1)

    def images_screen(self):
        test_empty = self.images.all()
        test_empty = len(test_empty)
        if test_empty:
            return (
                image
                for image in self.images.all()
                if image.scale == DocumentImage.SCREEN
            )
        else:
            return "no images"

    def date(self):
        date = self.dates.first()
        if date:
            return date.as_date()

    def slug(self):  # pragma: no cover
        # Try to extract the "genre term" from the descriptive title
        try:
            words = self.title.split(' ')
            n = 4
            while n < len(words) and words[n - 1] in (
                'a',
                'an',
                'the',
                'in',
                'of',
                'to',
                'at',
                'on',
                'and',
                'for',
            ):
                n += 1
            testing = slugify(' '.join(words[:n]))
            return slugify(' '.join(words[:n]))
        except:
            testing = "descriptive-title-missing"
            return testing

    def full_texts(self):
        """Fetch the DocumentText for this instance, if available.

        There is a one-to-many relationship between full-text docs and our
        documents described by metadata, deriving from the fact that each
        full-text doc -- with a few exceptions -- represents only one version
        of a given document, which often has up to four versions in our
        collection.

        The four versions all bear the same document code (also known as
        "Evidence File code" or "EF code", e.g., PS-398 or NOKW-222).

        """
        # ToDo: improve query by not needing the annotation and filtering.
        # Consider using instead:
        #   DocumentEvidenceCode.number
        #   DocumentEvidenceCode.prefix.code
        # (may need some extra prefetching for DocumentEvidencePrefix)

        # Do not use the plain `str` of DocumentEvidenceCode since for codes
        # with a suffix, the `str` representation will not match (like PS-343a)
        evidence_codes = [
            f'{e.prefix.code}-{e.number}' for e in self.evidence_codes.all()
        ]
        result = DocumentText.objects.annotate(
            evidence_code=Concat(
                'evidence_code_series', Value('-'), 'evidence_code_num'
            ),
        ).filter(evidence_code__in=evidence_codes)
        # XXX: sort in a meaningful way in the unlikely case there are multiple
        return result


class DocumentImage(models.Model):

    THUMB = 't'
    HALF = 'h'
    SCREEN = 's'
    DOUBLE = 'd'
    FULL = 'f'
    IMAGE_SCALES = (
        (THUMB, 'thumb'),
        (HALF, 'half'),
        (SCREEN, 'screen'),
        (DOUBLE, 'double'),
        (FULL, 'full'),
    )

    document = models.ForeignKey(
        Document, related_name='images', on_delete=models.PROTECT
    )
    page_number = models.IntegerField()
    physical_page_number = models.IntegerField(blank=True, null=True)

    # BEGIN DEPRECATED in favor of `image`
    _url = models.CharField(
        max_length=255, blank=True, null=True, db_column='url'
    )
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    # END DEPRECATED in favor of `image`

    scale = models.CharField(max_length=1, choices=IMAGE_SCALES)
    image_type = models.ForeignKey(
        'DocumentImageType', on_delete=models.PROTECT
    )
    image = models.ImageField(null=True, blank=True, storage=DocumentStorage())

    class Meta:
        ordering = ['page_number']

    def __str__(self):
        return "#{} Page {} {} {}x{}".format(
            self.document.id,
            self.page_number,
            self.scale,
            self.width,
            self.height,
        )

    @property
    def url(self):
        try:
            result = self.image.url
        except ValueError:
            result = self._url
            logger.exception(
                'No document image for "%s" (fallback %s)', self, result
            )
        return result

    def find_url(self, scale):
        if self.scale == scale:
            return self.url
        else:
            images = self.document.images.all()
            filter = (
                image
                for image in images
                if image.page_number == self.page_number
                and image.scale == scale
            )
            scaled = next(filter, None)
            if scaled:
                return scaled.url
            else:
                return None

    def thumb_url(self):
        return self.find_url(self.THUMB)

    def screen_url(self):
        return self.find_url(self.SCREEN)

    def full_url(self):
        return self.find_url(self.FULL)

    def image_tag(self):
        return (
            f'<a href="{self.url}"><img src="{self.url}" '
            f'alt="Scanned document page {self.page_number}" width=100 /></a>'
        )

    image_tag.allow_tags = True


class OldDocumentImage(models.Model):
    id = models.AutoField(primary_key=True, db_column='ImagesListID')
    document = models.ForeignKey(
        Document,
        related_name='old_images',
        on_delete=models.PROTECT,
        db_column='DocID',
    )

    page_number = models.IntegerField(db_column='PageSequenceNo')
    physical_page_number = models.CharField(
        max_length=50, db_column='PhysicalPageNo'
    )

    filename = models.CharField(
        db_column='FileName', max_length=8, blank=True, null=True
    )

    image_type = models.ForeignKey(
        'DocumentImageType', db_column='PageTypeID', on_delete=models.PROTECT
    )

    class Meta:
        managed = False
        db_table = 'tblImagesList'


class DocumentImageType(models.Model):
    id = models.AutoField(primary_key=True, db_column='PageTypeID')
    name = models.CharField(max_length=50, db_column='PageType')

    class Meta:
        managed = False
        db_table = 'tblPageTypes'

    def __str__(self):
        return self.name


class DocumentSource(models.Model):
    id = models.AutoField(primary_key=True, db_column='VersionID')
    name = models.CharField(max_length=50, db_column='Version')

    class Meta:
        managed = False
        db_table = 'tblVersions'

    def __str__(self):
        return self.name


class DocumentLanguage(models.Model):
    id = models.AutoField(primary_key=True, db_column='LanguageID')
    name = models.CharField(max_length=15, db_column='Language')

    class Meta:
        managed = False
        db_table = 'tblLanguages'

    def __str__(self):
        return self.name


class DocumentDate(models.Model):
    id = models.AutoField(primary_key=True, db_column='DatesOfDocListID')
    document = models.ForeignKey(
        Document,
        related_name='dates',
        on_delete=models.CASCADE,
        db_column='DocID',
    )

    day = models.IntegerField(db_column='DocDay')
    month = models.IntegerField(
        db_column='DocMonthID'
    )  # this is technically a foreign key but also just 1-indexed month number
    year = models.IntegerField(db_column='DocYear')

    class Meta:
        managed = False
        db_table = 'tblDatesOfDocList'

    def __str__(self):
        return '{}-{}-{}'.format(self.year, self.month, self.day)

    def as_date(self):
        doc_id = getattr(getattr(self, 'document', None), 'id', None)
        return parse_date(
            self.year, self.month, self.day, reference=f'document {doc_id}'
        )


class DocumentPersonalAuthorQuerySet(models.QuerySet):
    def metadata(self, **kwargs):
        return [
            author.metadata(**kwargs)
            for author in self.select_related('extra')
        ]

    def _metadata(self, **kwargs):
        # Given than ranks are not available via DB relationships (yet?), we
        # cache them all to avoid many queries when iterating over every author
        # property. This is total 3 queries! \o/
        ranks = dict(
            PersonalAuthorPropertyRank.objects.all().values_list(
                'name', 'rank'
            )
        )
        return [
            author._metadata(ranks, **kwargs)
            for author in self.prefetch_related('properties')
        ]


class DocumentPersonalAuthor(models.Model):
    id = models.AutoField(primary_key=True, db_column='PersonalAuthorID')
    last_name = models.CharField(max_length=35, db_column='AuthLName')
    first_name = models.CharField(max_length=25, db_column='AuthFName')
    title = models.CharField(max_length=100, db_column='AuthTitle')

    documents = models.ManyToManyField(
        Document,
        related_name='personal_authors',
        through='DocumentsToPersonalAuthors',
        through_fields=('author', 'document'),
    )

    objects = DocumentPersonalAuthorQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = 'tblPersonalAuthors'

    def __str__(self):
        return self.full_name()

    @cached_property
    def slug(self):
        return slugify(self.full_name())

    def full_name(self):
        if self.first_name and self.last_name:
            return '{} {}'.format(self.first_name, self.last_name)
        else:
            return self.first_name or self.last_name or 'Unknown'

    def metadata(self, minimal=False, ranks=None, backfill=False):
        try:
            result = self.extra.as_dict(minimal=minimal)
        except DocumentAuthorExtra.DoesNotExist:
            result = None

        if result is None:
            result = self._metadata(
                ranks=ranks, max_properties=0 if minimal else None
            )
            if backfill:
                # Create the corresponding `extra` instance to backfill entries
                # This is useful for future dump overwrites of the table for
                # DocumentPersonalAuthor, so this related model gets backfilled
                # automagically on demand.
                result = DocumentAuthorExtra.from_metadata(result).as_dict(
                    minimal=minimal
                )

        return result

    def _metadata(
        self,
        ranks=None,
        max_properties=None,
        max_property_values=None,
        max_qualifiers=None,
        max_qualifier_values=None,
    ):
        result = {
            'author': {
                'name': self.full_name(),
                'id': self.id,
                'slug': self.slug,
                'title': self.title,
                'description': '',
            },
        }

        # If no properties were requested, return early with base metadata
        if max_properties is not None and max_properties < 1:
            return result

        if ranks is None:  # reuse rank information between exploded properties
            ranks = dict(
                PersonalAuthorPropertyRank.objects.all().values_list(
                    'name', 'rank'
                )
            )

        # Properties grouped by name, then by qualifier
        grouped_props = defaultdict(lambda: {'rank': 0, 'prop_values': {}})

        # use all() with no modifiers, make use of potential prefetch_related
        for p in self.properties.all():
            rank = ranks.get(p.name)

            if rank is None or rank < 1:
                continue

            if not result['author']['description']:
                # use first non empty property to update author's description
                result['author']['description'] = p.personal_author_description

            key = p.name

            # handle special cases
            if key in ('family name', 'given name', 'birth name'):
                continue

            grouped_props[key]['rank'] = max(rank, grouped_props[key]['rank'])
            qualifiers = grouped_props[key]['prop_values'].setdefault(
                p.value, defaultdict(set)
            )
            # The qualifier "valid in place" can be suppressed altogether
            if p.qualifier and p.qualifier != 'valid in place':
                if not p.qualifier_value:
                    logger.info(
                        'No qualifier value for %s (author: %s, property: %s)',
                        p.qualifier,
                        self,
                        key,
                    )
                    continue

                qualifier = p.qualifier
                # The qualifier "object has role" can be simplified to "role"
                # (same for "subject has role")
                if qualifier in ('object has role', 'subject has role'):
                    qualifier = 'role'
                elif qualifier == 'point in time':
                    qualifier = 'date'

                qualifiers[qualifier].add(p.qualifier_value)

        # The properties "date of birth" and "place of birth" can be merged
        # into a single property thus: "born: 1900-03-19 (Berlin)" -- and
        # similarly for "date of death" and "place of death" resolving to
        # "died: 1945-03-09 (Wiesbaden)"
        for event, display_name in (('birth', 'born'), ('death', 'died')):
            place_of_event_dict = grouped_props.pop(f'place of {event}', {})
            place_of_event_rank = place_of_event_dict.get('rank', 0)
            place_of_event = place_of_event_dict.get('prop_values', {})

            date_of_event_dict = grouped_props.pop(f'date of {event}', {})
            date_of_event_rank = date_of_event_dict.get('rank', 0)
            date_of_event = date_of_event_dict.get('prop_values', {})

            if place_of_event and date_of_event:
                date_and_place = '{date} ({place})'.format(
                    date=' '.join(date_of_event.keys()),
                    place=' '.join(place_of_event.keys()),
                )
            elif place_of_event:
                date_and_place = ' '.join(place_of_event.keys())
            elif date_of_event:
                date_and_place = ' '.join(date_of_event.keys())
            else:
                continue

            # qualifiers for place and date
            qualifiers = [i.items() for i in place_of_event.values()] + [
                i.items() for i in date_of_event.values()
            ]
            # resulting merge by qualifier name
            merged_qualifiers = defaultdict(set)
            for q, qs in [i for items in qualifiers for i in items]:
                merged_qualifiers[q].update(qs)

            grouped_props[display_name] = {
                'prop_values': {date_and_place: merged_qualifiers},
                'rank': max(place_of_event_rank, date_of_event_rank),
            }

        for prop_name, prop_items in grouped_props.items():
            for prop_value, qualifiers in prop_items['prop_values'].items():
                prop_items['prop_values'][prop_value] = sorted_qualifiers = {
                    # sort the qualifier's values alphabetically
                    q: sorted(qs)[:max_qualifier_values]
                    for q, qs in qualifiers.items()
                }

                # handle special cases for qualifiers, mostly date related
                start = sorted_qualifiers.pop('start time', None)
                end = sorted_qualifiers.pop('end time', None)
                if start and not end:
                    sorted_qualifiers['since'] = start
                elif end and not start:
                    sorted_qualifiers['until'] = end
                elif start and end:
                    sorted_qualifiers['period'] = list(zip(start, end))

        image_urls = grouped_props.pop('image', {}).get('prop_values', {})
        if image_urls:
            first_image, qualifiers = list(image_urls.items())[0]
            # XXX: we need to properly handle "media legend" for images
            result['image'] = {
                'url': first_image,
                'alt': dict(qualifiers).pop(
                    'media legend', [f'Image of {self.full_name()}']
                )[0],
            }
        else:
            result['image'] = None

        # All other grouped props are mapped directly to the end result

        # If a given author doesn't have at least 10 ranked properties, display
        # only the ranked properties
        result['properties'] = sorted(
            (
                {
                    'rank': props['rank'],
                    'name': name,
                    # list of entities ordered by their rank DESC then name ASC
                    'prop_values': sorted(
                        (
                            {
                                'value': value,
                                'qualifiers': sorted(qualifiers.items())[
                                    :max_qualifiers
                                ],
                            }
                            for value, qualifiers in props[
                                'prop_values'
                            ].items()
                        ),
                        key=operator.itemgetter('value'),
                    )[:max_property_values],
                }
                for name, props in grouped_props.items()
            ),
            key=operator.itemgetter('rank'),
            reverse=True,
        )[:max_properties]

        return result


class DocumentsToPersonalAuthors(models.Model):
    id = models.AutoField(primary_key=True, db_column='PersonalAuthorsListID')
    document = models.ForeignKey(
        Document, db_column='DocID', on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        DocumentPersonalAuthor,
        db_column='PAuthNameID',
        on_delete=models.CASCADE,
    )

    class Meta:
        managed = False
        db_table = 'tblPersonalAuthorsList'


class DocumentGroupAuthor(models.Model):
    id = models.AutoField(primary_key=True, db_column='GroupAuthorID')
    name = models.CharField(max_length=25, db_column='GroupAuthorName')

    documents = models.ManyToManyField(
        Document,
        related_name='group_authors',
        through='DocumentsToGroupAuthors',
        through_fields=('author', 'document'),
    )

    class Meta:
        managed = False
        db_table = 'tblGroupAuthors'

    def __str__(self):
        return self.name if self.name is not None else '<None>'

    def short_name(self):
        return self.name.split(' (')[0]

    def metadata(self):
        name = self.short_name()
        return {
            'author': {
                'name': name,
                'id': self.id,
                'slug': slugify(name),
                'title': self.name if self.name is not None else '',
            }
        }


class DocumentsToGroupAuthors(models.Model):
    id = models.AutoField(primary_key=True, db_column='GroupAuthorsListID')
    document = models.ForeignKey(
        Document, db_column='DocID', on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        DocumentGroupAuthor, db_column='GANameID', on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = 'tblGroupAuthorsList'


class PersonalAuthorPropertyRank(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    name = models.CharField(db_column='Property', max_length=200, unique=True)
    instance_count = models.IntegerField(db_column='InstanceCount')
    rank = models.IntegerField(db_column='PropertyRank')
    load_timestamp = models.DateTimeField(db_column='LoadTimeStamp')

    class Meta:
        managed = False
        db_table = 'tblNurAuthorsWikidataPropertiesRanked'

    def __str__(self):
        return 'Property {} ranked as {} (count {})'.format(
            self.name, self.rank, self.instance_count
        )


class PersonalAuthorProperty(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    personal_author = models.ForeignKey(
        'DocumentPersonalAuthor',
        db_column='NTPPersonalAuthorID',
        on_delete=models.PROTECT,
        related_name='properties',
    )
    wikidata_id = models.CharField(db_column='WikidataID', max_length=100)
    personal_author_name = models.CharField(
        db_column='PersonalAuthorName', max_length=200
    )
    honorific = models.CharField(
        db_column='Honorific', max_length=100, blank=True
    )
    personal_author_description = models.CharField(
        db_column='PersonalAuthorDescription', max_length=1000
    )
    name = models.CharField(db_column='Property', max_length=100)
    value = models.CharField(db_column='Entity', max_length=200)
    qualifier = models.CharField(db_column='Qualifier', max_length=100)
    qualifier_value = models.CharField(db_column='QualValue', max_length=200)

    load_timestamp = models.DateTimeField(db_column='LoadTimestamp')

    class Meta:
        managed = False
        db_table = 'tblNurAuthorsWikidataPropertiesAndQualifiers'
        verbose_name_plural = 'Personal author properties'

    def __str__(self):
        qualifier = (
            f' ({self.qualifier}: {self.qualifier_value})'
            if self.qualifier
            else ''
        )
        return 'Property {} for {}: {}{}'.format(
            self.name,
            self.personal_author.full_name(),
            self.value,
            qualifier,
        )

    @cached_property
    def rank(self):
        result = (
            PersonalAuthorPropertyRank.objects.filter(name=self.name)
            .order_by('rank')
            .last()
        )
        if result:
            return result.rank


class DocumentAuthorExtraManager(models.Manager):
    def bulk_create_from_author_qs(
        self, author_qs, dry_run=False, force=False
    ):
        items = [
            self.model.from_metadata(metadata, dry_run, force, save=False)
            for metadata in author_qs._metadata()
        ]
        return self.bulk_create(items)

    def bulk_update_from_author_qs(
        self, author_qs, dry_run=False, force=False
    ):
        items = []
        for author in author_qs.select_related('extra'):
            metadata = author._metadata()
            author.extra.update_from_metadata(
                metadata, dry_run, force, save=False
            )
            items.append(author.extra)

        return self.bulk_update(
            items, fields=['description', 'image', 'image_alt', 'properties']
        )


class DocumentAuthorExtra(models.Model):
    author = models.OneToOneField(
        DocumentPersonalAuthor, related_name='extra', on_delete=models.CASCADE
    )
    description = models.TextField()
    image = models.ImageField(null=True, blank=True, storage=AuthorStorage())
    image_alt = models.CharField(max_length=1024)
    properties = models.JSONField()

    objects = DocumentAuthorExtraManager()

    @classmethod
    def process_image(cls, metadata, dry_run, force):
        if metadata['image'] is None:
            return None, ''

        image_url = metadata['image']['url']
        image_alt = metadata['image']['alt']
        image_name = f'{metadata["author"]["id"]}-{metadata["author"]["slug"]}'
        image_path = build_image_path(image_url, image_name)

        if dry_run:
            logger.info(
                f'Would download {image_url=} to {image_path=}, but dry-run '
                'was set'
            )
        else:
            download_and_store_image(
                image_url, image_path, AuthorStorage(), force
            )

        return image_path, image_alt

    @classmethod
    def from_metadata(cls, metadata, dry_run=False, force=False, save=True):
        image_path, image_alt = cls.process_image(metadata, dry_run, force)
        result = cls(
            author_id=metadata['author']['id'],
            description=metadata['author']['description'],
            image=image_path,
            image_alt=image_alt,
            properties=metadata['properties'],
        )
        if save:
            result.save()
        return result

    def update_from_metadata(
        self, metadata, dry_run=False, force=False, save=True
    ):
        image_path, image_alt = self.process_image(metadata, dry_run, force)
        self.description = metadata['author']['description']
        self.image = image_path
        self.image_alt = image_alt
        self.properties = metadata['properties']
        if save:
            self.save(
                update_fields=[
                    'description',
                    'image',
                    'image_alt',
                    'properties',
                ]
            )

    def as_dict(self, minimal=False):
        result = {
            'author': {
                'name': self.author.full_name(),
                'id': self.author.id,
                'slug': self.author.slug,
                'title': self.author.title,
                'description': self.description,
            }
        }
        if not minimal:
            image = (
                {'url': self.image.url, 'alt': self.image_alt}
                if self.image
                else None
            )
            result.update({'image': image, 'properties': self.properties})
        return result


class DocumentCase(models.Model):
    id = models.AutoField(primary_key=True, db_column='CaseID')
    name = models.CharField(max_length=100, db_column='Case_temp')

    documents = models.ManyToManyField(
        Document,
        related_name='cases',
        through='DocumentsToCases',
        through_fields=('case', 'document'),
    )

    class Meta:
        managed = False
        db_table = 'tblCases'

    def __str__(self):
        return self.name

    @property
    def tag_name(self):
        # cheating for now
        if self.id == 1:
            return 'IMT'
        elif self.id > 13:
            return 'Other'
        else:
            return 'NMT {}'.format(self.id - 1)

    def short_name(self):
        return self.name.split(' -')[0].replace('.', ':').replace(' 0', ' ')


class DocumentsToCases(models.Model):
    id = models.AutoField(primary_key=True, db_column='CasesListID')
    document = models.ForeignKey(
        Document, db_column='DocID', on_delete=models.CASCADE
    )
    case = models.ForeignKey(
        DocumentCase, db_column='DocCaseID', on_delete=models.CASCADE
    )

    prosecution_number = models.IntegerField(
        db_column='ProsExhNo', blank=True, null=True
    )
    prosecution_suffix = models.CharField(
        db_column='ProsExhNoSuffix', max_length=5, blank=True, null=True
    )
    prosecution_doc_book_number = models.IntegerField(
        db_column='ProsDocBkNo', blank=True, null=True
    )
    prosecution_doc_book_suffix = models.CharField(
        db_column='ProsDocBkNoSuffix', max_length=5, blank=True, null=True
    )

    # defexhnameid = models.IntegerField(db_column='DefExhNameID', blank=True, null=True)
    # defexhname = models.CharField(db_column='DefExhName', blank=True, null=True)
    # defexhno = models.IntegerField(db_column='DefExhNo', blank=True, null=True)
    # defexhnosuffix = models.CharField(db_column='DefExhNoSuffix', blank=True, null=True)

    defense_doc_name_id = models.IntegerField(
        db_column='DefDocNameID', blank=True, null=True
    )
    defense_doc_name = models.CharField(
        db_column='DefDocName', blank=True, null=True, max_length=50
    )
    defense_doc_number = models.IntegerField(
        db_column='DefDocNo', blank=True, null=True
    )
    defense_doc_suffix = models.CharField(
        db_column='DefDocNoSuffix', blank=True, null=True, max_length=30
    )

    defense_doc_book_name_id = models.IntegerField(
        db_column='DefDocBkNameID', blank=True, null=True
    )
    defense_doc_book_name = models.CharField(
        db_column='DefDocBkName', max_length=50, blank=True, null=True
    )
    defense_doc_book_number = models.IntegerField(
        db_column='DefDocBkNo', blank=True, null=True
    )
    defense_doc_book_suffix = models.CharField(
        db_column='DefDocBkNoSuffix', max_length=30, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = 'tblCasesList'


class DocumentCitation(models.Model):
    id = models.AutoField(primary_key=True, db_column='CasesDatesListID')
    document = models.ForeignKey(
        Document,
        related_name='citations',
        on_delete=models.CASCADE,
        db_column='DocID',
    )
    case = models.ForeignKey(
        DocumentCase, db_column='DocCaseID', on_delete=models.CASCADE
    )
    day = models.IntegerField(db_column='CaseDay')
    month = models.IntegerField(
        db_column='CaseMonthID'
    )  # this is technically a foreign key but also just 1-indexed month number
    year = models.IntegerField(db_column='CaseYear')
    transcript_page_number = models.IntegerField(db_column='EngTransPageNo')
    transcript_page_number_suffix = models.TextField(
        db_column='EngTransPageNoSuffix', null=True
    )

    class Meta:
        managed = False
        db_table = 'tblCasesDatesList'

    def __str__(self):
        result = f'{self.document} | {self.case} | {self.date} | {self.transcript_page_number}'
        if self.transcript_page_number_suffix:
            result += f'-{self.transcript_page_number_suffix}'
        return result

    @cached_property
    def date(self):
        doc_id = getattr(getattr(self, 'document', None), 'id', None)
        return parse_date(
            self.year,
            self.month,
            self.day,
            reference=f'document citation {doc_id}',
        )


class DocumentDefendantManager(models.Manager):
    """
    Filters out null names
    """

    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().exclude(first_name__isnull=True)


class DocumentDefendant(models.Model):
    objects = DocumentDefendantManager()

    id = models.AutoField(primary_key=True, db_column='DefendantID')
    last_name = models.CharField(max_length=110, db_column='DefLName')
    first_name = models.CharField(max_length=25, db_column='DefFName')
    case = models.ForeignKey(
        DocumentCase,
        related_name='defendants',
        db_column='CaseID',
        on_delete=models.CASCADE,
    )

    documents = models.ManyToManyField(
        Document,
        related_name='defendants',
        through='DocumentsToDefendants',
        through_fields=('defendant', 'document'),
    )

    class Meta:
        managed = False
        db_table = 'tblDefendants'

    def full_name(self):
        if self.first_name and self.last_name:
            return '{} {}'.format(self.first_name, self.last_name)
        else:
            return self.first_name or self.last_name or 'Unknown'


class DocumentsToDefendants(models.Model):
    id = models.AutoField(primary_key=True, db_column='DefendantsListID')
    document = models.ForeignKey(
        Document, db_column='DocID', on_delete=models.CASCADE
    )
    defendant = models.ForeignKey(
        DocumentDefendant, db_column='DefNameID', on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = 'tblDefendantsList'


class DocumentDefendantBookName(models.Model):
    id = models.AutoField(db_column='DefenseDocBkNameID', primary_key=True)
    name = models.TextField(db_column='DefenseDocBkName')
    case = models.ForeignKey(
        DocumentCase, db_column='CaseID', on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = 'tblDefenseDocBkNames'


class DocumentActivityManager(models.Manager):
    """
    Filters out first activity (No activity specified)
    """

    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().exclude(id=1)


class DocumentActivity(models.Model):
    objects = DocumentActivityManager()

    id = models.AutoField(primary_key=True, db_column='ActivityID')
    name = models.CharField(max_length=100, db_column='Activity')
    case = models.ForeignKey(
        DocumentCase,
        related_name='activities',
        db_column='CaseID',
        on_delete=models.CASCADE,
    )

    documents = models.ManyToManyField(
        Document,
        related_name='activities',
        through='DocumentsToActivities',
        through_fields=('activity', 'document'),
    )

    class Meta:
        managed = False
        db_table = 'tblActivities'
        verbose_name_plural = 'Document activities'

    def __str__(self):
        return self.name

    @property
    def short_name(self):
        # cheating for now
        return self.name.split(' (c')[0]


class DocumentsToActivities(models.Model):
    id = models.AutoField(primary_key=True, db_column='ActivitiesListID')
    document = models.ForeignKey(
        Document, db_column='DocID', on_delete=models.CASCADE
    )
    activity = models.ForeignKey(
        DocumentActivity, db_column='ActNameID', on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = 'tblActivitiesList'


class DocumentEvidencePrefix(models.Model):
    id = models.AutoField(
        db_column='NMTCodeID', primary_key=True
    )  # Field name made lowercase.
    code = models.CharField(
        db_column='NMTCode', max_length=5, blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tblNMTCodes'

    def __str__(self):
        return self.code


class DocumentEvidenceCode(models.Model):
    id = models.AutoField(
        db_column='NMTListID', primary_key=True
    )  # Field name made lowercase.
    prefix = models.ForeignKey(
        DocumentEvidencePrefix,
        db_column='NMTListCodeID',
        on_delete=models.PROTECT,
    )  # Field name made lowercase.
    document = models.ForeignKey(
        Document,
        related_name='evidence_codes',
        db_column='DocID',
        on_delete=models.CASCADE,
    )
    number = models.IntegerField(
        db_column='NMTNo', blank=True, null=True
    )  # Field name made lowercase.
    suffix = models.CharField(
        db_column='NMTNoText', max_length=25, blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tblNMTList'

    def __str__(self):
        return '{}-{}{}'.format(
            self.prefix.code, self.number, self.suffix or ''
        )


class DocumentExhibitCodeName(models.Model):
    id = models.AutoField(
        db_column='DefenseExhNameID', primary_key=True
    )  # Field name made lowercase.
    name = models.CharField(
        db_column='DefenseExhName', max_length=50, blank=True, null=True
    )  # Field name made lowercase.
    case = models.ForeignKey(
        DocumentCase, db_column='CaseID', on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = 'tblDefenseExhNames'


class DocumentExhibitCode(models.Model):
    id = models.AutoField(
        db_column='CasesListID', primary_key=True
    )  # Field name made lowercase.
    document = models.ForeignKey(
        Document,
        related_name='exhibit_codes',
        db_column='DocID',
        on_delete=models.CASCADE,
    )

    case = models.ForeignKey(
        DocumentCase, db_column='DocCaseID', on_delete=models.CASCADE
    )
    prosecution_number = models.IntegerField(
        db_column='ProsExhNo', blank=True, null=True
    )  # Field name made lowercase.
    prosecution_suffix = models.CharField(
        db_column='ProsExhNoSuffix', max_length=5, blank=True, null=True
    )  # Field name made lowercase.
    prosecution_doc_book_number = models.IntegerField(
        db_column='ProsDocBkNo', blank=True, null=True
    )  # Field name made lowercase.
    prosecution_doc_book_suffix = models.CharField(
        db_column='ProsDocBkNoSuffix', max_length=5, blank=True, null=True
    )  # Field name made lowercase.

    defense_name = models.ForeignKey(
        DocumentExhibitCodeName,
        db_column='DefExhNameID',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )  # Field name made lowercase.
    defense_name_denormalized = models.CharField(
        db_column='DefExhName', max_length=50, blank=True, null=True
    )
    defense_number = models.IntegerField(
        db_column='DefExhNo', blank=True, null=True
    )  # Field name made lowercase.
    defense_suffix = models.CharField(
        db_column='DefExhNoSuffix', max_length=5, blank=True, null=True
    )  # Field name made lowercase.

    defense_doc_name_id = models.IntegerField(
        db_column='DefDocNameID', blank=True, null=True
    )  # Field name made lowercase.
    defense_doc_name = models.CharField(
        db_column='DefDocName', max_length=50, blank=True, null=True
    )  # Field name made lowercase.

    defense_doc_number = models.IntegerField(
        db_column='DefDocNo', blank=True, null=True
    )  # Field name made lowercase.
    defense_doc_suffix = models.CharField(
        db_column='DefDocNoSuffix', max_length=5, blank=True, null=True
    )  # Field name made lowercase.
    defense_doc_book_name_id = models.IntegerField(
        db_column='DefDocBkNameID', blank=True, null=True
    )  # Field name made lowercase.
    defense_doc_book_name = models.CharField(
        db_column='DefDocBkName', max_length=50, blank=True, null=True
    )  # Field name made lowercase.
    defense_doc_book_number = models.IntegerField(
        db_column='DefDocBkNo', blank=True, null=True
    )  # Field name made lowercase.
    defense_doc_book_suffix = models.CharField(
        db_column='DefDocBkNoSuffix', max_length=5, blank=True, null=True
    )  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'tblCasesList'

    def __str__(self):
        if self.prosecution_number:
            return 'Prosecution {}{}'.format(
                self.prosecution_number, self.prosecution_suffix or ''
            )
        if self.defense_number:
            if self.defense_name:
                name = self.defense_name.name
            else:
                name = self.defense_name_denormalized or 'Defendant'
            return '{} {}{}'.format(
                name, self.defense_number, self.defense_suffix or ''
            )
        return ''


class DocumentTextQuerySet(models.QuerySet):
    def no_matching_document(self):
        evidence_codes = (
            DocumentEvidenceCode.objects.select_related(
                'prefix',
            )
            .filter(document_id__isnull=False, prefix_id__isnull=False)
            .annotate(
                evidence_code=Concat(
                    'prefix__code',
                    Value('-'),
                    'number',
                    Case(
                        When(suffix='', then=Value('')),
                        When(suffix__isnull=True, then=Value('')),
                        When(suffix__isnull=False, then='suffix'),
                    ),
                    output_field=models.CharField(),
                )
            )
            .values('evidence_code')
        )
        result = self.annotate(
            evidence_code=Concat(
                'evidence_code_series', Value('-'), 'evidence_code_num'
            ),
        ).exclude(evidence_code__in=Subquery(evidence_codes))
        return result


class DocumentText(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    title = models.CharField(db_column='Title', max_length=1000)
    evidence_code_tag = models.CharField(db_column='DocID', max_length=100)
    # could this be an FK to DocumentEvidencePrefix? (tblNMTCodes)
    evidence_code_series = models.CharField(
        db_column='DocCodeSeries', max_length=100
    )
    evidence_code_num = models.CharField(
        db_column='DocCodeNum', max_length=100
    )
    source_citation = models.CharField(
        db_column='SourceCitation', max_length=500
    )
    load_timestamp = models.DateTimeField(db_column='LoadDateTime')
    text = models.TextField(db_column='DocText', blank=True, null=True)

    objects = DocumentTextQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = 'tblNurembergDocTexts'

    def __str__(self):
        return f'{self.title}'

    @cached_property
    def evidence_code(self):
        return f'{self.evidence_code_series}-{self.evidence_code_num}'

    @cached_property
    def language_name(self):
        # Temporary default until a new dump of this table is provided with
        # lang information.
        return 'English'

    @cached_property
    def slug(self):
        return self.document.slug() if self.document else slugify(self.title)

    @cached_property
    def source_name(self):
        return self.source_citation

    @cached_property
    def total_pages(self):
        if not self.text:
            return 0

        # Some texts have both `680—PS` and `680-PS` as apparent page separator
        secondary_tag = self.evidence_code_tag.replace('-', '—')
        return (
            self.text.count(self.evidence_code_tag)
            + self.text.count(secondary_tag)
            + 1
        )

    @cached_property
    def document(self):
        return self.documents().first()

    def documents(self):
        """Fetch the most relevant Document for this DocumentText.

        As there can be multiple versions available for this metadata, we would
        like to use the metadata from the highest-ranked item from the
        following priority tree, if the full-text document is in English.
        If the full-text document is in German, d. and e. rise (in that order)
        to just below a.:

            a. Exhibit document (from any trial)
            b. English translation (EF doc)
            c. Staff Evidence analysis (EF doc)
            d. German typescript (EF doc)
            e. German photostat (EF doc)

        If no correlation can be found, then simply list the Title, DocID and
        Source from the full-text data table.

        In case of "a tie" for multiple documents with exhibit codes for the
        same evidence code, the following trial priority should be used:

            IMT
            NMT 11
            NMT 12
            NMT 6
            NMT 10
            NMT 9
            NMT 7
            NMT 8
            NMT 1
            NMT 3
            NMT 4
            NMT 5
            NMT 2

        """
        # Ensure that the evidence code number is an int to avoid ValueError
        # exceptions when filtering below.
        try:
            evidence_code_number = int(self.evidence_code_num)
        except ValueError:
            logger.info(
                'DocumentText: Can not search for related documents for text '
                '%s and evidence code %s (number: %s, series: %s)',
                self.id,
                self.evidence_code_tag,
                self.evidence_code_series,
                self.evidence_code_num,
            )
            return Document.objects.none()

        # Calculate trial exhibit priority as explained in the docstring
        cases_score = Case(
            When(exhibit_codes__case__name__startswith='IMT', then=100),
            When(exhibit_codes__case__name__startswith='NMT 11', then=12),
            When(exhibit_codes__case__name__startswith='NMT 12', then=11),
            When(exhibit_codes__case__name__startswith='NMT 06', then=10),
            When(exhibit_codes__case__name__startswith='NMT 10', then=9),
            When(exhibit_codes__case__name__startswith='NMT 09', then=8),
            When(exhibit_codes__case__name__startswith='NMT 07', then=7),
            When(exhibit_codes__case__name__startswith='NMT 08', then=6),
            When(exhibit_codes__case__name__startswith='NMT 01', then=5),
            When(exhibit_codes__case__name__startswith='NMT 03', then=4),
            When(exhibit_codes__case__name__startswith='NMT 04', then=3),
            When(exhibit_codes__case__name__startswith='NMT 05', then=2),
            When(exhibit_codes__case__name__startswith='NMT 02', then=1),
            default=Value(0),
        )
        # Calculate document source priority as explained above
        source_score = Case(
            When(source_id=1, then=10),  # Case Files/English
            When(source_id=9, then=9),  # Staff Evidence Analysis
            When(source_id=11, then=8),  # Typescript--German
            When(source_id=5, then=7),  # Photostat
            default=Value(0),
        )
        # We can't use `self.evidence_code_tag` because the ordering of series
        # and number varies (some have series-num, others have num-series).
        matches = (
            Document.objects.prefetch_related(
                'cases',
                'evidence_codes',
                'evidence_codes__prefix',
                'exhibit_codes',
                'source',
            )
            .filter(
                evidence_codes__number=evidence_code_number,
                evidence_codes__prefix__code=self.evidence_code_series,
            )
            .annotate(
                exhibit_codes_count=Count('exhibit_codes'),
                cases_score=cases_score,
                source_score=source_score,
            )
            .order_by(
                '-exhibit_codes_count',
                '-cases_score',
                '-source_score',
            )
        )
        # XXX: ToDo: match full-text language with document language. Currently
        # there is no way of knowing the full-text doc's lang.
        # A future dump of this table will include that piece of information.
        return matches
