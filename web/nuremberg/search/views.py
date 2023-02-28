from urllib import parse

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from haystack.generic_views import (
    FacetedSearchView,
    FacetedSearchMixin,
)
from nuremberg.documents.models import DocumentPersonalAuthor
from nuremberg.search.forms import (
    AdvancedDocumentSearchForm,
    DocumentSearchForm,
)
from nuremberg.search.lib.digg_paginator import DiggPaginator
from nuremberg.search.lib.solr_grouping_backend import GroupedSearchQuerySet


ADVANCED_SEARCH_FORM_ERRORS = 'advanced_search_form_errors'


class Search(FacetedSearchView):
    """
    This is a subclass of the default Haystack faceted search view to implement
    our modifications, including pagination, shorter query parameters, custom
    sorting, and labeled facets.

    You can add a search facet to the list simply by placing it in `facet_labels`.

    See `forms.py` for the faceting and fielded search logic itself.
    """

    load_all = False
    queryset = GroupedSearchQuerySet()

    # page numbers like [1, 2 ... 6, 7, 8, 9, 10, ... 19, 20]
    paginator_class = DiggPaginator
    paginate_by = 15
    context_pages = 4
    edge_pages = 2

    form_class = DocumentSearchForm
    search_field = 'q'
    filter_field = 'f'
    material_field = 'm'
    sort_field = 'sort'
    default_sort = 'relevance'

    facet_labels = (
        ('Material Type', 'material_type'),
        ('Trial', 'case_names'),
        ('Defendant', 'defendants'),
        ('Date', 'date_year'),
        ('Author', 'authors'),
        ('Language', 'language'),
        ('Source', 'source'),
        ('Trial Issues', 'trial_activities'),
    )
    facet_to_label = {field: label for (label, field) in facet_labels}
    facet_fields = [label[1] for label in facet_labels]

    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except Http404:  # pragma: no cover
            if self.request.GET.get('page', 1) == 1:
                raise
        params = self.request.GET.copy()
        del params['page']
        return redirect('%s?%s' % (self.request.path, params.urlencode()))

    def form_invalid(self, form):  # pragma: no cover
        # override SearchView to give a blank search by default
        # TODO: this seems unnecessary, so ignoring from coverage
        self.queryset = form.search()
        context = self.get_context_data(
            **{self.form_name: form, 'object_list': self.get_queryset()}
        )
        return self.render_to_response(context)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                'sort_results': self.request.GET.get(
                    self.sort_field, self.default_sort
                ),
                'selected_facets': self.request.GET.getlist(self.filter_field),
                'facet_to_label': self.facet_to_label,
            }
        )
        return kwargs

    def get_queryset(self):
        # override FacetedSearchMixin
        qs = super(FacetedSearchMixin, self).get_queryset()
        for field in self.facet_fields:
            sort = 'count'
            qs = qs.facet(field, missing=True, sort=sort, mincount=1)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # pull the query out of form so it is pre-processed
        context['query'] = q = context['form'].data.get('q') or ''
        if context['facets']:
            labeled_facets = []
            for (label, field) in self.facet_labels:
                counts = context['facets']['fields'].get(field, [])
                # missing ignores mincount and sorting
                if (None, 0) in counts:
                    counts.remove((None, 0))
                else:
                    pass
                    # sort missing into the other facet values
                    # counts.sort(key=lambda field: field[1], reverse=True)
                labeled_facets.append(
                    {'field': field, 'label': label, 'counts': counts}
                )
            context.update({'labeled_facets': labeled_facets})

        if context['form']:
            context['facet_lookup'] = {}
            for (field, value, facet) in context['form'].applied_filters:
                context['facet_lookup'][facet] = True

        if self.request.GET.get('partial'):
            context['base_template'] = 'search/partial.html'
        else:
            context['base_template'] = None

        # Lastly, fetch author metadata (once per author), and flag text-only
        # results so we can customize details links and improve title
        author_ids = set()
        for i in context['object_list']:
            for result in i.documents or []:
                author_ids.update(
                    ap['author']['id']
                    for ap in (result.authors_properties or [])
                )
                # Results for full-text docs without a matching document image
                # should point to the mode=text doc details URL
                if result.model_name.lower() == 'documenttext':
                    result.mode = 'text'
                else:
                    result.mode = 'image'

        context['authors_metadata'] = {
            metadata['author']['id']: metadata
            for metadata in DocumentPersonalAuthor.objects.filter(
                id__in=author_ids
            ).metadata()
        }

        errors = self.request.session.pop(ADVANCED_SEARCH_FORM_ERRORS, {})
        form = AdvancedDocumentSearchForm.from_search_qs(qs=q, errors=errors)
        context['advanced_search_form'] = form
        return context

    def get_paginator(self, *args, **kwargs):
        return self.paginator_class(
            *args, body=self.context_pages, tail=self.edge_pages, **kwargs
        )


class NewSearch(Search):
    """Temporarily duplicated search view for ViteJS integration"""

    template_name = 'search/new-search.html'


@csrf_exempt
def advanced_search(request):
    form = AdvancedDocumentSearchForm(data=request.POST)
    if form.is_valid():
        q = form.as_search_qs()
    else:
        q = form.as_search_qs(request.POST)

    if form.errors:
        # Add form errors to the session for the GET search response to render
        request.session[ADVANCED_SEARCH_FORM_ERRORS] = form.errors
        # Add a generic error message that will be displayed at the advanced
        # form toplevel
        messages.error(
            request,
            _('The provided advanced search terms are invalid or incomplete.'),
        )
        # Lastly, for every form error, add an "overloaded" error message with
        # the error encoded as JSON. This will be rendered in the `search.html`
        # template as <script> blocks to allow for more fancy error showing,
        # in a potentail future improvement of the UI.
        for field, error in form.errors.items():
            messages.error(request, error.as_json(), extra_tags=field)

    qs = parse.urlencode({Search.search_field: q})
    return redirect(reverse('search:search') + '?' + qs + '#advanced')
