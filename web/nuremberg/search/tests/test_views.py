import json
import re
from urllib import parse

import pytest
from django.http import QueryDict
from django.urls import reverse

from nuremberg.core.tests.acceptance_helpers import (
    client,
    follow_link,
    go_to,
)
from nuremberg.search.forms import AdvancedDocumentSearchForm
from nuremberg.search.templatetags.search_url import search_url
from nuremberg.search.views import ADVANCED_SEARCH_FORM_ERRORS
from nuremberg.transcripts.models import Transcript


SEARCH_SUMMARY_SELECTOR = '[data-test="search-result-pages-summary"]'
pytestmark = pytest.mark.django_db


@pytest.fixture
def query():
    def get_query(query=''):
        return go_to(search_url(query))

    return get_query


def test_search_page(query):
    page = query('')

    search_bar = page('input[type="search"]')
    assert search_bar
    assert search_bar.val() == '*'

    assert re.findall(
        r'Results 1-15 of \d+ for \*', page(SEARCH_SUMMARY_SELECTOR).text()
    )
    assert re.findall(r'Document \(\d+\)', page('.facet').text())

    page = follow_link(page('.facet p').with_text('Transcript').find('a'))

    assert 'Results 1-5 of 5 for *' in page(SEARCH_SUMMARY_SELECTOR).text()
    assert 'Document' not in page('.facet').text()
    filter_link = (
        page('.applied-filters')
        .with_text('Material Type Transcript')
        .find('a')
    )
    assert filter_link

    page = follow_link(filter_link)


def test_facets(query):
    page = query('polish workers in germany')

    baseline = (  # baseline query
        r'Results 1-15 of \d+ for polish workers in germany'
    )
    assert re.findall(baseline, page(SEARCH_SUMMARY_SELECTOR).text())

    # test adding facet
    page = follow_link(page('.facet p').with_text('NMT 2').find('a'))
    assert re.findall(
        r'Results 1-15 of \d+ for polish workers in germany',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert 'NMT 2' in page('.applied-filters').with_text('Trial').text()

    # test removing facet
    page = follow_link(
        page('.applied-filters').with_text('Trial NMT 2').find('a')
    )
    assert re.findall(baseline, page(SEARCH_SUMMARY_SELECTOR).text())

    # test unknown facet
    page = follow_link(
        page('.facet')
        .with_text('Trial')
        .find('p')
        .with_text('Unknown')
        .find('a')
    )
    assert re.findall(
        r'Results 1-15 of \d+ for polish workers in germany',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert 'None' in page('.applied-filters').with_text('Trial').text()

    # test multiple facets
    page = follow_link(
        page('.facet')
        .with_text('Language')
        .find('p')
        .with_text('English')
        .find('a')
    )
    assert re.findall(
        r'Results 1-15 of \d+ for polish workers in germany',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert 'None' in page('.applied-filters').with_text('Trial').text()
    assert 'English' in page('.applied-filters').with_text('Language').text()

    page = follow_link(
        page('.facet')
        .with_text('Source')
        .find('p')
        .with_text('Typescript')
        .find('a')
    )
    assert re.findall(
        'Results 1-15 of \d+ for polish workers in germany',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert 'None' in page('.applied-filters').with_text('Trial').text()
    assert 'English' in page('.applied-filters').with_text('Language').text()
    assert 'Typescript' in page('.applied-filters').with_text('Source').text()

    # test date range
    date_range = page('.facet').with_text('Date').find('form')
    from_name = date_range.find('input[type=number]').nth(0).attr('name')
    to_name = date_range.find('input[type=number]').nth(1).attr('name')
    page = go_to(date_range.submit_url({from_name: 1940, to_name: 1941}))
    assert re.findall(
        r'Results 1-3 of 3 for polish workers in germany',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert 'None' in page('.applied-filters').with_text('Trial').text()
    assert 'English' in page('.applied-filters').with_text('Language').text()
    assert 'Typescript' in page('.applied-filters').with_text('Source').text()
    assert '1940-1941' in page('.applied-filters').with_text('Date').text()
    assert '1940' in page('.document-row').text()
    assert '1941' in page('.document-row').text()

    # test removing all filters
    page = follow_link(page('a').with_text('Clear all filters'))
    assert re.findall(baseline, page(SEARCH_SUMMARY_SELECTOR).text())


def test_keyword_search(query):
    page = query('')
    search_bar = page('input[type="search"]')
    page = go_to(search_bar.submit_value('experiments'))

    assert re.findall(
        r'Results 1-15 of \d+ for experiments',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert len(page('.document-row')) == 15

    page = follow_link(
        page('.facet')
        .with_text('Material Type')
        .find('p')
        .with_text('Transcript')
        .find('a')
    )
    transcript_row = page('.document-row').with_text(
        'Transcript for NMT 1: Medical Case'
    )
    assert transcript_row
    assert '30 January 1947' in transcript_row.text()

    page = follow_link(transcript_row.find('a'))
    assert '5680 pages with results' in page.text()
    assert 'We will than proceed to the next\nexperiment' in page('p').text()

    page = follow_link(page('a').with_text('Page 32'))
    assert 'HLSL Seq. No. 8' in page.text()


@pytest.fixture
def count_results(query):
    def _count(q, count=None, page_count=15, first_count=1):
        page = query(q)
        matches = re.findall(
            r'Results (\d+)-(\d+) of (\d+) for (.*)',
            page('.results-count').text(),
        )
        assert len(matches) == 1
        [(first, page_size, total, search_query)] = matches
        assert int(first) == first_count
        assert int(page_size) == page_count
        if count is None:
            assert int(total) > 0
        else:
            assert int(total) == count
        assert search_query == q
        return int(total)

    return _count


def test_field_search(count_results):

    count_results('workers')
    count_results('workers author:fritz')
    count_results('workers date:january')
    count_results('workers -trial:(nmt 4)')
    count_results('workers evidence:NO-190', page_count=5)
    count_results('workers source:typescript language:german')
    count_results(
        'workers source:typescript language:german -author:Milch', 29
    )
    count_results('workers trial:(nmt 2 | nmt 4)')

    total = count_results('workers date:unknown')
    count_results('workers date:none', total)

    total = count_results('workers -date:none')
    count_results('workers -date:none notafield:(no matches)', total)

    count_results('workers trial:(nmt 2 | nmt 4) author:speer|fritz')
    count_results('workers author:"hitler adolf"', 0, 0, 0)
    count_results('workers author:"adolf hitler"')
    count_results('workers exhibit:prosecution')
    count_results('* author:"adolf hitler" -author:adolf', 0, 0, 0)
    count_results('* exhibit:handloser')
    count_results('malaria')
    count_results('freezing')
    count_results('malaria freezing')
    count_results('-malaria freezing')
    count_results('malaria -freezing')
    count_results('malaria | freezing')


def test_document_search(query):
    page = query('workers')
    assert re.findall(
        r'Results 1-15 of \d+ for workers',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    page = follow_link(
        page('.document-row a').with_text(
            'Instructions concerning the treatment of Eastern domestic '
            'workers in Germany'
        )
    )

    search_bar = page('input[type=search]')
    assert search_bar
    assert search_bar.val() == 'workers'

    page = go_to(search_bar.submit_value('instructions'))
    assert re.findall(
        r'Results 1-15 of \d+ for instructions',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )

    q = 'instructions for air force medical'
    page = go_to(search_bar.submit_value(q))
    matches = re.findall(
        r'Results 1-15 of \d+ for ([\w\s]+)',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert matches == [q]

    page = follow_link(
        page('.document-row a').with_text(
            'Instructions for air force medical officers regarding freezing'
        )
    )

    search_bar = page('input[type=search]')
    assert search_bar
    assert search_bar.val() == q

    page = follow_link(page('a').with_text('Back to search results'))
    matches = re.findall(
        r'Results 1-15 of \d+ for ([\w\s]+)',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert matches == [q]


def test_landing_search(query):
    page = go_to(reverse('content:landing'))

    search_bar = page('input[type=search]')
    assert search_bar

    page = go_to(search_bar.submit_value('workers'))
    assert re.findall(
        r'Results 1-15 of \d+ for workers',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )

    page = go_to(reverse('content:landing'))

    # uncheck Documents
    search_bar = page('input[type=search]')
    form = search_bar.closest('form')
    values = QueryDict('', mutable=True)
    values[search_bar.attr('name')] = 'workers'
    values.setlist(
        form.find('label').with_text('Documents').find('input').attr('name'),
        ['transcripts', 'photographs'],
    )
    page = go_to(form.submit_url(values, defaults=False))

    assert re.findall(
        r'Results 1-7 of 7 for workers type:transcripts|photographs',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )


def test_transcript_snippets(query):
    page = query('documents type:transcript')

    matches = re.findall(
        r'Results 1-(\d+) of (\d+) for documents type:transcript',
        page(SEARCH_SUMMARY_SELECTOR).text(),
    )
    assert len(matches) == 1
    [(page_size, total)] = matches
    assert page_size == total
    assert int(total) == Transcript.objects.all().count()

    assert '4039 results in this transcript' in page.text()

    # snippets on several pages
    assert '... p. 8350' in page.text()
    assert '... p. 8963' in page.text()
    assert '... p. 144' in page.text()

    # test single page results
    page = query('documents hlsl:2')

    assert (
        'Results 1-1 of 1 for documents hlsl:2'
        in page(SEARCH_SUMMARY_SELECTOR).text()
    )
    assert '1 result in this transcript' in page.text()

    # all snippets from first page
    assert '[ ... p. 26 ] can work on it' in page.text()
    assert '[ ... p. 26 ] possible with these few\ndocuments' in page.text()
    assert '[ ... p. 26 ] able to select which\ndocuments' in page.text()

    # test no snippets
    page = query('type:transcript')

    # text from several pages
    assert '... p. unlabeled' in page.text()
    assert '... p. 26' in page.text()
    assert '... p. 27' in page.text()

    # test single page no snippets
    page = query('type:transcript')

    # one snippet
    assert '... p. unlabeled' in page.text()
    assert '[ ... ]' in page.text()


def test_pagination(query):
    page = query('')

    matches = re.findall(
        r'Results 1-15 of (\d+) for \*', page(SEARCH_SUMMARY_SELECTOR).text()
    )
    assert matches

    page = follow_link(page('[data-test="search-result-last-page"]'))

    total_search_results = int(matches[0])
    i = total_search_results - (total_search_results % 15) + 1
    assert (
        f'Results {i}-{total_search_results} of {total_search_results} for *'
        in page(SEARCH_SUMMARY_SELECTOR).text()
    )


def test_sort(query):
    # testing "relevance" might be too brittle for now
    page = query('experiments')
    assert 'Argument: Final plea for Karl Gebhardt' in page.text()

    page = follow_link(page('[data-test="search-result-last-page"]'))
    assert 'Unknown' in page.text()

    # test date sorts
    page = query('-date:none')
    page = go_to(
        page.absolute_url(
            page('select option').with_text('Earliest Date').val()
        )
    )
    earliest_date = '15 May 1871'
    latest_date = '03 September 1948'
    assert earliest_date in page.text()
    page = follow_link(page('[data-test="search-result-last-page"]'))
    assert latest_date in page.text()

    page = query('-date:none')
    page = go_to(
        page.absolute_url(page('select option').with_text('Latest Date').val())
    )
    assert latest_date in page.text()
    page = follow_link(page('[data-test="search-result-last-page"]'))
    assert earliest_date in page.text()

    # test page sorts
    page = query('')
    page = go_to(
        page.absolute_url(page('select option').with_text('Most Pages').val())
    )
    assert '492 pages' in page.text()
    last_page_link = page('[data-test="search-result-last-page"]')
    page = follow_link(last_page_link)
    assert '0 pages' in page.text()

    page = query('')
    page = go_to(
        page.absolute_url(
            page('select option').with_text('Fewest Pages').val()
        )
    )
    assert '0 pages' in page.text()
    page = follow_link(page('[data-test="search-result-last-page"]'))
    assert '492 pages' in page.text()


def test_search_partial():
    url = reverse('search:search') + '?partial=1'
    response = client.get(url)

    assert response.status_code == 200


def test_search_invalid_page():
    url = reverse('search:search') + '?q=foo&page=-1'
    response = client.get(url)

    assert response.status_code == 302
    assert response['Location'] == reverse('search:search') + '?q=foo'


def test_advanced_search_form_available():
    url = reverse('search:search')
    response = client.get(url)

    assert isinstance(
        response.context.get('advanced_search_form'),
        AdvancedDocumentSearchForm,
    )


def test_advanced_search_post_no_errors():
    url = reverse('search:advanced-search')
    data = {'keywords': 'foo bar'}
    response = client.post(url, data=data, follow=False)

    assert response.status_code == 302
    qs = parse.urlencode({'q': 'keywords:"foo bar"'}) + '#advanced'
    assert response['Location'] == reverse('search:search') + '?' + qs


def test_advanced_search_post_with_errors():
    url = reverse('search:advanced-search')
    data = {'author': 'Does not exist'}
    response = client.post(url, data=data, follow=False)

    assert response.status_code == 302
    qs = parse.urlencode({'q': 'author:"Does not exist"'}) + '#advanced'
    assert response['Location'] == reverse('search:search') + '?' + qs

    errors = client.session.get(ADVANCED_SEARCH_FORM_ERRORS)
    assert errors is not None
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert errors == form.errors

    response = client.get(response['Location'])
    assert response.status_code == 200

    invalid_choice = [
        {
            'message': (
                'Select a valid choice. Does not exist is not one of the '
                'available choices.'
            ),
            'code': 'invalid_choice',
        },
    ]
    messages = response.context['messages']
    actual = [m.message for m in messages if not m.extra_tags] + [
        (m.extra_tags, json.loads(m.message)) for m in messages if m.extra_tags
    ]
    expected = [
        'The provided advanced search terms are invalid or incomplete.',
        ('author', invalid_choice),
    ]
    assert actual == expected


def test_bug_repro():
    response = client.get(reverse('search:test'), follow=True)

    error = response.context['request'].session.get('a-key')
    assert error is None
