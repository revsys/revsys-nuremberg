import json

from haystack import indexes
from nuremberg.documents.models import Document, DocumentText


class JsonField(indexes.CharField):

    # ToDo: redefine prepare as well?
    # https://django-haystack.readthedocs.io/en/latest/searchfield_api.html#prepare

    def convert(self, value):
        value = super().convert(value)
        if value is not None:
            value = json.loads(value)
        return value


class DocumentIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    highlight = indexes.CharField(model_attr='text')
    material_type = indexes.CharField(default='Document', faceted=True)
    grouping_key = indexes.FacetCharField(
        facet_for='grouping_key'
    )  # not really a facet, just an exact key

    slug = indexes.CharField(model_attr='slug', indexed=False)
    title = indexes.CharField(model_attr='title', default='')
    literal_title = indexes.CharField(model_attr='literal_title', null=True)
    description = indexes.CharField(model_attr='description', null=True)

    total_pages = indexes.IntegerField(
        model_attr='total_pages', default=0, null=True
    )
    date = indexes.CharField(faceted=True, null=True)
    date_year = indexes.CharField(faceted=True, null=True)
    date_sort = indexes.DateTimeField(model_attr='date', null=True)

    language = indexes.CharField(
        model_attr='language__name', faceted=True, null=True
    )
    source = indexes.CharField(
        model_attr='source__name', faceted=True, null=True
    )

    authors = indexes.MultiValueField(faceted=True, null=True)
    authors_properties = JsonField(null=True, indexed=False)
    defendants = indexes.MultiValueField(faceted=True, null=True)
    case_names = indexes.MultiValueField(faceted=True, null=True)
    case_tags = indexes.MultiValueField(faceted=True, null=True)

    evidence_codes = indexes.MultiValueField(null=True)
    exhibit_codes = indexes.MultiValueField(null=True)
    book_codes = indexes.MultiValueField(null=True)

    trial_activities = indexes.MultiValueField(faceted=True, null=True)

    def get_model(self):
        return Document

    def get_updated_field(self):
        return 'updated_at'

    def index_queryset(self, using=None):
        return (
            Document.objects.select_related()
            .prefetch_related(
                'activities',
                'cases',
                'dates',
                'evidence_codes',
                'evidence_codes__prefix',
                'exhibit_codes',
                'exhibit_codes__defense_name',
                'personal_authors',
                'group_authors',
                'defendants',
            )
            .all()
        )

    def prepare_grouping_key(self, document):
        # This is a hack to group transcripts but not documents in a single query.
        # Transcripts get a group key, documents get a unique key.
        # This can be changed to make grouping work on volume or something else.
        return 'Document_{}'.format(document.id)

    def prepare_authors(self, document):
        return [
            author.short_name() for author in document.group_authors.all()
        ] + [author.full_name() for author in document.personal_authors.all()]

    def prepare_authors_properties(self, document):
        result = [
            author.metadata() for author in document.group_authors.all()
        ] + document.personal_authors.all().metadata(minimal=True)
        # json modifiers for the most compact json representation
        return json.dumps(result, indent=None, separators=(',', ':'))

    def prepare_trial_activities(self, document):
        return [activity.short_name for activity in document.activities.all()]

    def prepare_date(self, document):
        date = document.date()
        if date:
            return date.strftime('%d %B %Y')

    def prepare_date_year(self, document):
        date = document.date()
        if date:
            return date.year

    def prepare_defendants(self, document):
        return [
            defendant.full_name() for defendant in document.defendants.all()
        ]

    def prepare_case_names(self, document):
        return [case.short_name() for case in document.cases.all()]

    def prepare_case_tags(self, document):
        return [case.tag_name for case in document.cases.all()]

    def prepare_evidence_codes(self, document):
        return [str(code) for code in document.evidence_codes.all()]

    def prepare_exhibit_codes(self, document):
        codes = []
        for code in document.exhibit_codes.all():
            if str(code):
                codes.append(str(code))
        return codes

    def prepare_book_codes(self, document):
        return [
            code.book_code
            for code in document.exhibit_codes.all()
            if code.book_code
        ]


class DocumentTextIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    highlight = indexes.CharField(model_attr='text')
    material_type = indexes.CharField(default='Document', faceted=True)
    grouping_key = indexes.FacetCharField(
        facet_for='grouping_key'
    )  # XXX: needed???

    slug = indexes.CharField(model_attr='slug', indexed=False)
    title = indexes.CharField(model_attr='title', default='')
    source = indexes.CharField(model_attr='source_citation')

    total_pages = indexes.IntegerField(model_attr='total_pages')

    evidence_codes = indexes.MultiValueField()  # Match what DocumentIndex has

    def get_model(self):
        return DocumentText

    def get_updated_field(self):
        return 'load_timestamp'

    def index_queryset(self, using=None):
        # Filter those DocumentText that have no matching document. The ones
        # with at least one matching document will be indexed along with the
        # class above DocumentIndex
        return DocumentText.objects.no_matching_document()

    def prepare_grouping_key(self, obj):
        # This is a hack to group transcripts but not other objects.
        return 'DocumentText_{}'.format(obj.id)

    def prepare_evidence_codes(self, obj):
        return [obj.evidence_code]
