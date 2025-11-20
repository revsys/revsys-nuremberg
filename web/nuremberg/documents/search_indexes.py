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
    highlight = indexes.CharField(null=True)
    material_type = indexes.CharField(default='Document Image', faceted=True)
    grouping_key = indexes.FacetCharField(
        facet_for='grouping_key'
    )  # not really a facet, just an exact key

    slug = indexes.CharField(model_attr='slug', indexed=False)
    title = indexes.CharField(default='')
    literal_title = indexes.CharField(model_attr='literal_title', null=True)
    description = indexes.CharField(model_attr='description', null=True)

    total_pages = indexes.IntegerField(
        model_attr='total_pages', default=0, null=True
    )
    date = indexes.CharField(faceted=True, null=True)
    date_year = indexes.CharField(faceted=True, null=True)
    date_sort = indexes.DateTimeField(null=True)

    language = indexes.CharField(
        model_attr='language__name', faceted=True, null=True
    )
    source = indexes.CharField(
        model_attr='source__name', faceted=True, null=True
    )
    hlsl = indexes.CharField(null=True)
    authors = indexes.MultiValueField(faceted=True, null=True)
    authors_properties = JsonField(null=True, indexed=False)
    defendants = indexes.MultiValueField(faceted=True, null=True)
    case_names = indexes.MultiValueField(faceted=True, null=True)
    case_tags = indexes.MultiValueField(faceted=True, null=True)

    evidence_codes = indexes.MultiValueField(null=True)
    exhibit_codes = indexes.MultiValueField(null=True)
    book_codes = indexes.MultiValueField(null=True)

    trial_activities = indexes.MultiValueField(faceted=True, null=True)
    related_document_ids = indexes.MultiValueField(null=True)

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

    def prepare_title(self, document):
        """Use display_title property which provides fallback for missing titles."""
        return document.display_title

    def prepare_authors(self, document):
        return [
            author.short_name() for author in document.group_authors.all()
        ] + [author.full_name() for author in document.personal_authors.all()]

    def prepare_authors_properties(self, document):
        result = {
            'group': [a.metadata() for a in document.group_authors.all()],
            'person': document.personal_authors.all().metadata(minimal=True),
        }
        # json modifiers for the most compact json representation
        return json.dumps(result, indent=None, separators=(',', ':'))

    def prepare_trial_activities(self, document):
        return [activity.short_name for activity in document.activities.all()]

    def prepare_date(self, document):
        date = document.date()
        if date:
            return date.as_str_flexible()

    def prepare_date_year(self, document):
        date = document.date()
        if date:
            return date.year

    def prepare_date_sort(self, document):
        """Convert document date to a valid datetime for SOLR sorting.

        Returns None if the date components are invalid, which is acceptable
        since the field is marked as null=True.
        """
        date_obj = document.date()
        if date_obj:
            # Use the as_date() method which safely parses year/month/day
            return date_obj.as_date()
        return None

    def prepare_defendants(self, document):
        return [
            defendant.full_name() for defendant in document.defendants.all()
        ]

    def prepare_case_names(self, document):
        return [case.short_name() for case in document.cases.all()]

    def prepare_case_tags(self, document):
        return [case.tag_name for case in document.cases.all()]

    def prepare_evidence_codes(self, document):
        codes = []
        for code in document.evidence_codes.all():
            code_str = str(code)
            # Filter out codes with broken foreign keys (will show as "NO_PREFIX-123")
            if code_str and not code_str.startswith("NO_PREFIX"):
                codes.append(code_str)
        return codes

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

    def prepare_hlsl(self, document):
        return document.pk

    def prepare_related_document_ids(self, document):
        return [t.id for t in document.full_texts()]


class DocumentTextIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    highlight = indexes.CharField(model_attr='text')
    material_type = indexes.CharField(
        default='Document Full Text', faceted=True
    )
    grouping_key = indexes.FacetCharField(
        facet_for='grouping_key'
    )  # XXX: needed???

    slug = indexes.CharField(model_attr='slug', indexed=False)
    # The title of the most relevant DocumentImage linked with this text
    title = indexes.CharField(default='')
    # The actual title of the document full text, which is usually less nice
    # (e.g. TRANSLATION OF DOCUMENT 2115-PS)
    literal_title = indexes.CharField(default='')
    total_pages = indexes.IntegerField(
        model_attr='total_pages', default=0, null=True
    )

    date = indexes.CharField(faceted=True, null=True)
    date_year = indexes.CharField(faceted=True, null=True)
    date_sort = indexes.DateTimeField(null=True)

    source = indexes.CharField(model_attr='source_citation')

    authors = indexes.MultiValueField(faceted=True, null=True)
    authors_properties = JsonField(null=True, indexed=False)

    evidence_codes = indexes.MultiValueField()  # Match what DocumentIndex has
    related_document_ids = indexes.MultiValueField(null=True)

    def get_model(self):
        return DocumentText

    def get_updated_field(self):
        return 'load_timestamp'

    def index_queryset(self, using=None):
        return DocumentText.objects.all()

    def prepare_grouping_key(self, obj):
        # This is a hack to group transcripts but not other objects.
        return 'DocumentText_{}'.format(obj.id)

    def prepare_title(self, obj):
        """Use display_title from linked Document, if available."""
        if obj.document:
            return obj.document.display_title
        return obj.display_title

    def prepare_literal_title(self, obj):
        """Use display_title property which provides fallback for missing titles."""
        return obj.display_title

    def prepare_authors(self, obj):
        document = obj.document
        if document is None:
            return []

        return [
            author.short_name() for author in document.group_authors.all()
        ] + [author.full_name() for author in document.personal_authors.all()]

    def prepare_authors_properties(self, obj):
        document = obj.document
        if document is None:
            result = {}
        else:
            result = {
                'group': [a.metadata() for a in document.group_authors.all()],
                'person': document.personal_authors.all().metadata(minimal=True),
            }
        # json modifiers for the most compact json representation
        return json.dumps(result, indent=None, separators=(',', ':'))

    def prepare_date(self, obj):
        date = obj.document and obj.document.date()
        if date:
            return date.as_str_flexible()

    def prepare_date_year(self, obj):
        date = obj.document and obj.document.date()
        if date:
            return date.year

    def prepare_date_sort(self, obj):
        """Convert document date to a valid datetime for SOLR sorting.

        Returns None if the date components are invalid, which is acceptable
        since the field is marked as null=True.
        """
        if obj.document:
            date_obj = obj.document.date()
            if date_obj:
                # Use the as_date() method which safely parses year/month/day
                return date_obj.as_date()
        return None

    def prepare_evidence_codes(self, obj):
        return [obj.evidence_code]

    def prepare_related_document_ids(self, obj):
        return [i.id for i in obj.documents()]
