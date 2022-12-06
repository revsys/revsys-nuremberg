import re
from collections import deque

from django import forms
from django.utils.translation import gettext_lazy as _
from haystack.forms import SearchForm
from haystack.inputs import AutoQuery

from nuremberg.documents.models import (
    DocumentActivity,
    DocumentCase,
    DocumentEvidencePrefix,
    DocumentExhibitCode,
    DocumentExhibitCodeName,
    DocumentGroupAuthor,
    DocumentLanguage,
    DocumentPersonalAuthor,
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
        print(
            '\n\n\n======= FieldedSearchForm sort_results', self.sort_results
        )
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


class AdvancedDocumentSearchForm(forms.Form):

    MATCH_ALL = 'all'
    MATCH_ANY = 'any'
    MATCH_CHOICES = [
        (MATCH_ALL, _('all')),
        (MATCH_ANY, _('any of')),
    ]
    AUTHOR_CHOICES = (
        [('', _('Choose author'))]
        + sorted(
            (i.full_name(), i.full_name())
            for i in DocumentPersonalAuthor.objects.all()
        )
        + sorted(
            (i.name, i.name)
            for i in DocumentGroupAuthor.objects.all()
            .filter(name__isnull=False)
            .exclude(name='')
        )
    )
    DEFENDANT_CHOICES = [('', _('Choose defendant'))] + [
        (i, i)
        for i in DocumentExhibitCodeName.objects.filter(name__isnull=False)
        .exclude(name='')
        .order_by('name')
        .values_list('name', flat=True)
        .distinct()
    ]
    ISSUE_CHOICES = [('', _('Choose trial issues'))] + [
        (i, i)
        for i in DocumentActivity.objects.all()
        .order_by('name')
        .values_list('name', flat=True)
        .distinct()
    ]
    TRIAL_CHOICES = [('', _('Choose trial'))] + [
        (case.tag_name, case.short_name)
        for case in DocumentCase.objects.filter(id__lt=14)
        .distinct()
        .order_by('id')
    ]
    EVIDENCE_PREFIX_CHOICES = [('', _('Choose Series'))] + [
        (prefix.code, prefix.code)
        for prefix in DocumentEvidencePrefix.objects.all()
        .distinct()
        .order_by('code')
    ]
    EXHIBIT_CHOICES = [('prosecution', _('Prosecution'))] + [
        (i, i)
        for i in DocumentExhibitCode.objects.filter(
            defense_name_denormalized__isnull=False
        )
        .order_by('defense_name_denormalized')
        .values_list('defense_name_denormalized', flat=True)
        .distinct()
    ]
    BOOK_CHOICES = [('prosecution', _('Prosecution'))] + [
        (i, i)
        for i in DocumentExhibitCode.objects.filter(
            defense_doc_book_name__isnull=False
        )
        .exclude(defense_doc_book_name=0)
        .order_by('defense_doc_book_name')
        .values_list('defense_doc_book_name', flat=True)
        .distinct()
    ]
    LANGUAGE_CHOICES = [('', _('Choose language'))] + [
        (lang.name.lower(), lang.name)
        for lang in DocumentLanguage.objects.all().order_by('id')
    ]
    match = forms.ChoiceField(choices=MATCH_CHOICES, required=True)
    keywords = forms.CharField(required=False)
    title = forms.CharField(required=False)
    author = forms.ChoiceField(required=False, choices=AUTHOR_CHOICES)
    defendant = forms.ChoiceField(required=False, choices=DEFENDANT_CHOICES)
    issue = forms.ChoiceField(
        label=_('Trial Issues'), required=False, choices=ISSUE_CHOICES
    )
    trial = forms.ChoiceField(required=False, choices=TRIAL_CHOICES)
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
    # document_book = forms.ChoiceField(required=False, choices=BOOK_CHOICES)
    # document_book_num = forms.CharField(
    #     required=False,
    #     widget=forms.TextInput(
    #         attrs={'size': '10', 'placeholder': _('Number')}
    #     ),
    # )
    language = forms.ChoiceField(required=False, choices=LANGUAGE_CHOICES)
    notes = forms.CharField(required=False)
    source = forms.CharField(required=False)

    def as_search_qs(self):
        data = self.cleaned_data
        op = ' ' if data['match'] == self.MATCH_ALL else ' | '
        terms = []
        # XXX: search by notes and document book missing
        for term in (
            'keywords',
            'title',
            'author',
            'defendant',
            'issue',
            'trial',
            'language',
            'notes',
            'source',
        ):
            value = data.get(term)
            if value:
                terms.append(f'{term}:"{value}"')

        # special treatment
        evidence = data.get('evidence')
        evidence_num = data.get('evidence_num')
        if evidence and evidence_num:
            suffix = data.get('evidence_suffix', '')
            terms.append(
                f'evidence:{"-".join((evidence, evidence_num))}{suffix}'
            )

        exhibit = data.get('exhibit')
        exhibit_num = data.get('exhibit_num')
        if exhibit and exhibit_num:
            terms.append(f'exhibit:"{" ".join((exhibit, exhibit_num))}"')

        # Should some terms be q and some others be f and/or m, etc?
        q = op.join(terms)
        return q

    @classmethod
    def from_search_qs(cls, qs):
        # XXX: ToDo
        return cls()
