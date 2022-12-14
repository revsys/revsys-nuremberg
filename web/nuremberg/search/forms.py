import re
from collections import deque

from django import forms
from django.forms import ValidationError
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from haystack.forms import SearchForm
from haystack.inputs import AutoQuery

from nuremberg.documents.models import (
    EVIDENCE_CODE_RE,
    EXHIBIT_CODE_RE,
    DocumentActivity,
    DocumentCase,
    DocumentEvidencePrefix,
    DocumentExhibitCode,
    DocumentExhibitCodeName,
    DocumentGroupAuthor,
    DocumentLanguage,
    DocumentPersonalAuthor,
    DocumentSource,
)


class EmptyFacetsSearchForm(SearchForm):
    """Extended search form to support empty facets and year periods.

    This reimplementation of FacetedSearchForm enables two additional features:

    - filtering by missing facet values (like Date: Unknown)
    - date_year range filtering like 1940-1945, as a search filter

    """

    applied_filters = []
    date_range = [None, None]

    def __init__(self, *args, **kwargs):
        self.facet_to_label = dict(kwargs.pop('facet_to_label'))
        self.selected_facets = kwargs.pop('selected_facets')
        super().__init__(*args, **kwargs)
        if 'year_min' in self.data and 'year_max' in self.data:
            self.selected_facets = [
                f
                for f in self.selected_facets
                if not f.startswith('date_year')
            ]
            self.selected_facets.append(
                'date_year:{}-{}'.format(
                    self.data['year_min'], self.data['year_max']
                )
            )

    def search(self):
        sqs = super().search()
        self.applied_filters = []
        for facet in self.selected_facets:
            if ":" not in facet:
                continue

            field, value = facet.split(":", 1)

            field_label = self.facet_to_label[field]
            if not field_label:
                continue

            self.applied_filters.append((field_label, value, facet))

            if field == 'date_year' and '-' in value:
                self.date_range = value.split('-', 1)
                sqs = sqs.narrow(
                    u'date_year_exact:[%s TO %s]'
                    % (
                        sqs.query.clean(self.date_range[0]),
                        sqs.query.clean(self.date_range[1]),
                    )
                )
                # sqs = sqs.filter(date_year__range=self.date_range)
            else:
                if value == 'None':
                    sqs = sqs.narrow(u'-%s_exact:[* TO *]' % (field))
                elif value:
                    sqs = sqs.narrow(
                        u'%s_exact:"%s"' % (field, sqs.query.clean(value))
                    )

        return sqs


class FieldedSearchForm(SearchForm):
    """Natural fielded search form.

    This form enables natural fielded search with the format:

    general search terms field:field search terms -field:excluded field search terms

    The relevant logic is in `parse_query` and `apply_field_query`.

    The query is parsed into one `auto_query` and many `field_queries`. Each
    field_query is tagged to render whether it is included, excluded, or
    ignored.

    You can add an additional search field by adding its name to
    `search_fields`, along with the Solr index key if different.

    To enable grouping of TranscriptPage index objects under a single
    transcript, we use an experiment modification to the Haystack Solr Backend.
    Many search parameters are replaced with their group-query equivalents. Be
    cautious when modifying grouping parameters, as the results can be
    counter-intuitive.

    NOTE: Transcript search results require all keywords to match on a single
    page.

    Highlighting is used in transcript and document text search results, and as
    a way to count "occurrences" within transcript search.

    """

    auto_query = None
    field_queries = []
    sort_fields = {
        'date-asc': 'date_sort',
        'date-desc': '-date_sort',
        'relevance': '-score',
        'pages-asc': 'total_pages',
        'pages-desc': '-total_pages',
        'page': 'seq_number',
    }

    search_fields = {
        'all': 'text',
        'keywords': 'text',
        'title': 'title',
        'author': 'authors',
        'authors': True,
        'defendant': 'defendants',
        'defendants': True,
        'hlsl': 'django_id',
        'case': 'case_names',
        'trial': 'case_names',
        'type': 'material_type',
        'date': True,
        'language': True,
        'notes': 'description',
        'description': True,
        'source': True,
        'evidence': 'evidence_codes',
        'exhibit': 'exhibit_codes',
        'book': 'book_codes',
        'activity': 'trial_activities',
        'activities': 'trial_activities',
        'issue': 'trial_activities',
        'issues': 'trial_activities',
    }
    material_types = ('documents', 'transcripts', 'photographs')

    def __init__(self, *args, **kwargs):
        self.sort_results = kwargs.pop('sort_results')
        self.transcript_id = kwargs.pop('transcript_id', None)

        super().__init__(*args, **kwargs)
        if 'm' in self.data:
            included = self.data.getlist('m')
            self.data = self.data.copy()
            if len(included) < 3:
                self.data['q'] += ' type:{}'.format('|'.join(included))

    def search(self):
        sort = self.sort_fields.get(self.sort_results, 'score')
        sqs = self.searchqueryset

        if self.transcript_id:
            sqs = sqs.filter(
                material_type='Transcript', transcript_id=self.transcript_id
            ).order_by(sort)
            # use snippets to count "occurrences" of a match in transcript
            # search results
            highlight_snippets = 10
        else:
            # use grouping by document/transcript id to cluster all transcript
            # page results together weirdly it uses a separate sort field
            if sort.startswith('-'):
                sort = sort[1:] + ' desc'
            else:
                sort += ' asc'
            sqs = sqs.group_by(
                'grouping_key',
                {
                    'group.sort': sort + ', seq_number asc',
                    'group.limit': 3,
                    'sort': sort,
                },
            )
            highlight_snippets = 3

        if not self.is_valid() or not 'q' in self.cleaned_data:
            return sqs

        (self.auto_query, self.field_queries) = self.parse_query_keywords(
            self.cleaned_data['q']
        )

        self.highlight_query = ''

        if self.auto_query and not re.match(r'^\s*\*\s*$', self.auto_query):
            sqs = self.apply_field_query(sqs, ['all', self.auto_query])

        for field_query in self.field_queries:
            sqs = self.apply_field_query(sqs, field_query)

        if self.highlight_query:
            hlq = AutoQuery(self.highlight_query).prepare(sqs.query)
            sqs = sqs.highlight(
                **{
                    'hl.snippets': highlight_snippets,
                    'hl.fragsize': 150,
                    'hl.q': f'material_type:transcripts AND highlight:({hlq})',
                    'hl.fl': 'highlight',
                    'hl.requireFieldMatch': 'true',
                    'hl.simple.pre': '<mark>',
                    'hl.simple.post': '</mark>',
                }
            )

        return sqs

    def parse_query_phrases(self, full_query):  # pragma: no cover
        """Parser that extracts unmarked phrase queries for fields.

        eg: date:January 2

        """
        sections = deque(re.split(r'(\-?\w+)\:', full_query))
        auto_query = sections.popleft()
        field_queries = []
        while len(sections) >= 2:
            field_queries.append([sections.popleft(), sections.popleft()])
        return (auto_query, field_queries)

    def parse_query_keywords(self, full_query):
        """Parser that extracts single field keyword queries

        Also extract () keyword groups or "" exact matches.
        e.g. date:(January 2)

        """
        sections = re.split(
            r'((?:\-?\w+)\s*\:\s*(?:"[^"]+"|\([^:]+\)|[\w\-\+\.\|]+))',
            full_query,
        )
        auto_query = sections[0]
        field_queries = []
        for query in sections[1:]:
            if ':' in query:
                field_queries.append(query.split(':', 1))
            else:
                field_queries.append([None, query])
        return (auto_query, field_queries)

    def apply_field_query(self, sqs, field_query):
        (field, value) = field_query

        if not value or value.isspace():
            return sqs

        if not field:
            field = 'all'

        if field[0] == '-':
            exclude = True
            field = field[1:]
        else:
            exclude = False

        field_key = self.search_fields.get(field)
        if field_key == True:
            field_key = field

        # the solr backend aggressively quotes OR queries, so we must build an
        # OR query manually to keep our loose keyword search
        if field_key:
            values = re.split(r'[|]', value)
            query_list = []
            for value in values:
                if re.match(
                    r'^\s*"?(none|unknown)"?\s*$', value, re.IGNORECASE
                ):
                    query_list.append(
                        '(-{}: [* TO *] AND *:*)'.format(field_key)
                    )
                else:
                    # to enable snippets for exhibit codes we must add them to
                    # the highlight query
                    if field_key in (
                        'exhibit_codes',
                        'evidence_codes',
                        'text',
                    ):
                        self.highlight_query += ' ' + value
                    # NOTE: field_key is whitelisted above
                    query_list.append(
                        '{}:({})'.format(
                            field_key, AutoQuery(value).prepare(sqs.query)
                        )
                    )
            raw_query = '({})'.format(' OR '.join(query_list))
            if exclude:
                field_query.append('excluded')
                raw_query = 'NOT {}'.format(raw_query)
            else:
                field_query.append('included')
            sqs = sqs.raw_search(raw_query)
        else:
            field_query.append('ignored')

        return sqs


class DocumentSearchForm(EmptyFacetsSearchForm, FieldedSearchForm):
    pass


CHOICE_EMPTY = ('', _('Choose one...'))


class AdvancedDocumentSearchForm(forms.Form):

    AUTHOR_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + sorted(
            (i.full_name(), i.full_name())
            for i in DocumentPersonalAuthor.objects.all()
        )
        + sorted(
            (i.name, i.name)
            for i in DocumentGroupAuthor.objects.all()
            .filter(name__isnull=False)
            .exclude(name='')
        ),
        list,
    )
    DEFENDANT_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + [
            (i, i)
            for i in DocumentExhibitCodeName.objects.filter(name__isnull=False)
            .exclude(name='')
            .order_by('name')
            .values_list('name', flat=True)
            .distinct()
        ],
        list,
    )
    ISSUE_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + [
            (i.short_name, i.short_name)
            for i in DocumentActivity.objects.all().order_by('name').distinct()
            if i.short_name
        ],
        list,
    )
    TRIAL_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + [
            (case.tag_name, case.short_name)
            for case in DocumentCase.objects.filter(id__lt=14)
            .distinct()
            .order_by('id')
        ],
        list,
    )
    EVIDENCE_PREFIX_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + [
            (prefix.code, prefix.code)
            for prefix in DocumentEvidencePrefix.objects.all()
            .distinct()
            .order_by('code')
        ],
        list,
    )
    EXHIBIT_CHOICES = lazy(
        lambda: [CHOICE_EMPTY, ('Prosecution', _('Prosecution'))]
        + [
            (i, i)
            for i in DocumentExhibitCode.objects.filter(
                defense_name_denormalized__isnull=False
            )
            .order_by('defense_name_denormalized')
            .values_list('defense_name_denormalized', flat=True)
            .distinct()
        ],
        list,
    )
    BOOK_CHOICES = lazy(
        lambda: [CHOICE_EMPTY, ('Prosecution', _('Prosecution'))]
        + [
            (i, i)
            for i in DocumentExhibitCode.objects.filter(
                defense_doc_book_name__isnull=False
            )
            .exclude(defense_doc_book_name=0)
            .order_by('defense_doc_book_name')
            .values_list('defense_doc_book_name', flat=True)
            .distinct()
        ],
        list,
    )
    LANGUAGE_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + [
            (lang.name.lower(), lang.name)
            for lang in DocumentLanguage.objects.all().order_by('name')
        ],
        list,
    )
    SOURCE_CHOICES = lazy(
        lambda: [CHOICE_EMPTY]
        + [
            (source.name, source.name)
            for source in DocumentSource.objects.all().order_by('id')
            if source.name.lower() != 'unspecified'
        ],
        list,
    )
    keywords = forms.CharField(required=False)
    title = forms.CharField(required=False)
    notes = forms.CharField(required=False)
    author = forms.ChoiceField(required=False, choices=AUTHOR_CHOICES)
    defendant = forms.ChoiceField(required=False, choices=DEFENDANT_CHOICES)
    issue = forms.ChoiceField(
        label=_('Trial Issues'), required=False, choices=ISSUE_CHOICES
    )
    trial = forms.ChoiceField(required=False, choices=TRIAL_CHOICES)
    language = forms.ChoiceField(required=False, choices=LANGUAGE_CHOICES)
    source = forms.ChoiceField(required=False, choices=SOURCE_CHOICES)

    # Evidence, Exhibit and Book fields should really be MultiValueField
    # https://docs.djangoproject.com/en/4.1/ref/forms/fields/#multivaluefield

    evidence = forms.ChoiceField(
        label=_('Evidence File Code'),
        required=False,
        choices=EVIDENCE_PREFIX_CHOICES,
    )
    evidence_num = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'size': '10', 'placeholder': _('Number')}
        ),
    )
    evidence_suffix = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'size': '10', 'placeholder': _('Suffix')}
        ),
    )
    exhibit = forms.ChoiceField(
        label=_('Trial Exhibit'), required=False, choices=EXHIBIT_CHOICES
    )
    exhibit_num = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'size': '10', 'placeholder': _('Number')}
        ),
    )
    book = forms.ChoiceField(
        label=_('Document Book'), required=False, choices=BOOK_CHOICES
    )
    book_num = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'size': '10', 'placeholder': _('Number')}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        # Handle evidence, exhibit and book codes using the combined widgets.
        # See comment above about ideally using MultiWidget
        # https://docs.djangoproject.com/en/4.1/ref/forms/widgets/#django.forms.MultiWidget

        evidence = cleaned_data.get('evidence')
        evidence_num = cleaned_data.get('evidence_num')
        if bool(evidence) != bool(evidence_num):
            self.add_error(
                'evidence',
                ValidationError('Evidence code is incomplete', code='invalid'),
            )
        elif evidence:
            suffix = cleaned_data.get('evidence_suffix', '')
            cleaned_data[
                'evidence_code'
            ] = f'{evidence}-{evidence_num}{suffix}'

        exhibit = cleaned_data.get('exhibit')
        exhibit_num = cleaned_data.get('exhibit_num')
        if bool(exhibit) != bool(exhibit_num):
            self.add_error(
                'exhibit',
                ValidationError(
                    'Exhibit information is incomplete',
                    code='invalid',
                ),
            )
        elif exhibit:
            cleaned_data['exhibit_code'] = f'{exhibit} {exhibit_num}'

        book = cleaned_data.get('book')
        book_num = cleaned_data.get('book_num')
        if bool(book) != bool(book_num):
            self.add_error(
                'book',
                ValidationError(
                    'Book information is incomplete', code='invalid'
                ),
            )
        elif book:
            cleaned_data['book_code'] = f'{book} {book_num}'

        return cleaned_data

    def as_search_qs(self, data=None):
        # Allow search qs to be built both from form's data or any other data
        if data is None:
            data = self.cleaned_data

        terms = []
        # free-form entries, need to properly handle empty spaces within field
        for term in (
            'keywords',
            'title',
            'notes',
        ):
            values = data.get(term, '').split(' ')
            terms.extend(f'{term}:{value}' for value in values if value)

        # choice field entries
        for term in (
            'author',
            'defendant',
            'issue',
            'trial',
            'language',
            'source',
        ):
            value = data.get(term)
            if value:
                terms.append(f'{term}:"{value}"')

        # special treatment, uses `_code` suffix for field name
        for term in ('evidence', 'exhibit', 'book'):
            value = data.get(f'{term}_code')
            if value:
                terms.append(f'{term}:"{value}"')

        # This assumes AND operation between search fields
        q = ' '.join(terms)
        return q

    @classmethod
    def from_search_qs(cls, qs, errors=None):
        # This assumes AND operation between search fields
        expr = re.compile(r'([a-z0-9_]+):("[^"]+"|[^"\s]+)\s*')
        initial = {}
        for k, v in expr.findall(qs):
            v = v.strip('"')
            if k in initial:
                # support advanced search syntax using multiple occurrences of
                # the same field name, for example:
                # q=keywords:euthanasia keywords:disabled
                # should result in initial['keywords'] = 'euthanasia disabled'
                initial[k] += ' ' + v
            else:
                initial[k] = v

        # handle evidence code
        evidence = initial.get('evidence')
        if evidence:
            matches = EVIDENCE_CODE_RE.match(evidence)
            if matches:
                evidence, evidence_num, evidence_suffix = matches.groups()
                initial['evidence'] = evidence
                initial['evidence_num'] = evidence_num
                initial['evidence_suffix'] = evidence_suffix

        # handle exhibit and book codes similarly to how evidence is handled
        exhibit = initial.get('exhibit')
        if exhibit:
            matches = EXHIBIT_CODE_RE.match(exhibit)
            if matches:
                exhibit, exhibit_num = matches.groups()
                initial['exhibit'] = exhibit
                initial['exhibit_num'] = exhibit_num

        book = initial.get('book')
        if book:
            matches = EXHIBIT_CODE_RE.match(book)
            if matches:
                book, book_num = matches.groups()
                initial['book'] = book
                initial['book_num'] = book_num

        result = cls(data=initial)

        if errors:
            result.cleaned_data = {}
            for field, error in errors.items():
                result.add_error(field, error)

        return result
