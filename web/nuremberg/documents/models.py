import datetime
import logging
import operator
from collections import defaultdict

from django.utils.text import slugify
from django.db import models
from django.db.models import Value
from django.db.models.functions import Concat

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
                str(e) + ' (got year %r, month %r, day %r)',
                self.year,
                self.month,
                self.day,
            )
            result = None  # this is an issue
        return result


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

    class Meta:
        managed = False
        db_table = 'tblPersonalAuthors'

    def __str__(self):
        return self.full_name()

    def full_name(self):
        if self.first_name and self.last_name:
            return '{} {}'.format(self.first_name, self.last_name)
        else:
            return self.first_name or self.last_name or 'Unknown'


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
        return 'Property {} for {}: {} ({}: {})'.format(
            self.name,
            self.personal_author.full_name(),
            self.value,
            self.qualifier,
            self.qualifier_value,
        )

    @property
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


def author_metadata(author_name, max_length=10):
    properties = PersonalAuthorProperty.objects.filter(
        personal_author_name=author_name
    )

    # Group properties by name, this may need a more complex algorithm
    grouped_props = defaultdict(list)
    for p in properties:
        if p.rank is None or p.rank < 1:
            continue
        key = p.name
        # handle special cases
        if key in ('family name', 'given name'):
            key = 'name'
        elif key in ('place of birth', 'date of birth'):
            key = 'born'
        elif key in ('place of death', 'date of death'):
            key = 'died'
        else:
            key = p.name
        grouped_props[key].append((p.rank, p.entity))

    image_urls = grouped_props.pop('image', None)
    if image_urls:
        # XXX: we need to properly handle "media legend" for images
        image = {
            'url': sorted(image_urls)[0][1],
            'alt': grouped_props.pop(
                'media_legend', f'Image of {author_name}'
            ),
        }
    else:
        image = None

    # If a given author doesn't have at least 10 ranked properties, display
    # only the ranked properties
    metadata = sorted(
        (
            {
                'rank': max(i[0] for i in matches),  # maximun rank
                'name': name,
                # list of entities ordered by their individual rank in reverse
                'values': [
                    i[1] for i in sorted(matches, key=lambda x: (-x[0], x[1]))
                ],
            }
            for name, matches in grouped_props.items()
        ),
        key=operator.itemgetter('rank'),
        reverse=True,
    )[:max_length]

    if not metadata:
        author = (
            DocumentPersonalAuthor.objects.annotate(
                full_name=Concat('first_name', Value(' '), 'last_name')
            )
            .filter(full_name=author_name)
            .first()
        )
        if author and author.title:
            metadata = [{'rank': 1, 'name': 'title', 'values': [author.title]}]

    result = {
        'author': {'name': author_name},
        'image': image,
        'metadata': metadata,
    }
    return result
