import datetime
import logging
import operator
from collections import defaultdict

from django.db import models
from django.utils.functional import cached_property
from django.utils.text import slugify

from nuremberg.core.storages import DocumentStorage


logger = logging.getLogger(__name__)


class Document(models.Model):
    id = models.AutoField(primary_key=True, db_column='DocID')
    title = models.CharField(max_length=255, db_column='TitleDescriptive')
    literal_title = models.TextField(db_column='Title')
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
        return '<a href="{0}"><img src="{0}" alt="Scanned document page {1}" width=100 /></a>'.format(
            self.url, self.page_number
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
        try:
            result = datetime.date(self.year, self.month, self.day)
        except (TypeError, ValueError) as e:
            logging.warning(
                'Error parsing date for document %s: %s '
                '(got year %r, month %r, day %r)',
                getattr(self, 'document', None),
                e,
                self.year,
                self.month,
                self.day,
            )
            result = None  # this is an issue
        return result


class DocumentPersonalAuthorQuerySet(models.QuerySet):
    def metadata(self, max_length=10):
        # Given than ranks are not available via DB relationships (yet?), we
        # cache them all to avoid many queries when iterating over every author
        # property. This is total 3 queries! \o/
        ranks = dict(
            PersonalAuthorPropertyRank.objects.all().values_list(
                'name', 'rank'
            )
        )
        return [
            author.metadata(ranks, max_length)
            for author in self.prefetch_related('properties')
        ]


DocumentPersonalAuthorManager = DocumentPersonalAuthorQuerySet.as_manager


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

    objects = DocumentPersonalAuthorManager()

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

    def metadata(self, ranks=None, max_length=10):
        result = {
            'author': {
                'name': self.full_name(),
                'id': self.id,
                'slug': self.slug,
                'title': self.title,
                'description': '',
            },
            'image': None,
            'properties': [],
        }

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
                    logging.warning(
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

        # The merging of properties and qualifiers should display property
        # followed by the qualifier in parentheses:
        # "property: property value (qualifier: qualifier value)"
        # e.g., "participant in: Nuremberg Medical Trial (role: prosecutor)"

        # For the qualifiers "start time" and "end time" for some property. On
        # the front end, we'd like to simply see a parenthesized expression
        # with the two dates separated by "through":
        # "1933-10-15 through 1936-11-01"

        for prop_name, prop_items in grouped_props.items():
            for prop_value, qualifiers in prop_items['prop_values'].items():
                prop_items['prop_values'][prop_value] = sorted_qualifiers = {
                    # sort the qualifier's values alphabetically
                    q: sorted(qs)
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
                    sorted_qualifiers['period'] = start + end

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
                                'qualifiers': sorted(qualifiers.items()),
                            }
                            for value, qualifiers in props[
                                'prop_values'
                            ].items()
                        ),
                        key=operator.itemgetter('value'),
                    ),
                }
                for name, props in grouped_props.items()
            ),
            key=operator.itemgetter('rank'),
            reverse=True,
        )[:max_length]

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
    loadtimestamp = models.DateTimeField(db_column='LoadTimeStamp')

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

    loadtimestamp = models.DateTimeField(db_column='LoadTimestamp')

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


class DocumentCase(models.Model):
    id = models.AutoField(primary_key=True, db_column='CaseID')
    name = models.CharField(max_length=100, db_column='Case_temp')

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

    documents = models.ManyToManyField(
        Document,
        related_name='cases',
        through='DocumentsToCases',
        through_fields=('case', 'document'),
    )

    class Meta:
        managed = False
        db_table = 'tblCases'


class DocumentsToCases(models.Model):
    id = models.AutoField(primary_key=True, db_column='CasesListID')
    document = models.ForeignKey(
        Document, db_column='DocID', on_delete=models.CASCADE
    )
    case = models.ForeignKey(
        DocumentCase, db_column='DocCaseID', on_delete=models.CASCADE
    )

    class Meta:
        managed = False
        db_table = 'tblCasesList'


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
    defense_suffix = models.CharField(
        db_column='DefExhNoSuffix', max_length=5, blank=True, null=True
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
