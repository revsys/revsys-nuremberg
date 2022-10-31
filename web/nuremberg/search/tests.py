import pytest
from django.http import QueryDict
from django.urls import reverse

from nuremberg.core.tests.acceptance_helpers import (
    follow_link,
    go_to,
)
from nuremberg.search.templatetags.search_url import search_url


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

    assert 'Results 1-15 of 14553 for *' in page('p').text()
    assert 'Document (14329)' in page('.facet').text()

    page = follow_link(page('.facet p').with_text('Transcript').find('a'))

    assert 'Results 1-5 of 5 for *' in page('p').text()
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

    # baseline
    assert 'Results 1-15 of 41 for polish workers in germany' in page.text()

    # test adding facet
    page = follow_link(page('.facet p').with_text('NMT 2').find('a'))
    assert 'Results 1-8 of 8 for polish workers in germany' in page.text()
    assert 'NMT 2' in page('.applied-filters').with_text('Trial').text()

    # test removing facet
    page = follow_link(
        page('.applied-filters').with_text('Trial NMT 2').find('a')
    )
    assert 'Results 1-15 of 41 for polish workers in germany' in page.text()

    # test unknown facet
    page = follow_link(
        page('.facet')
        .with_text('Trial')
        .find('p')
        .with_text('Unknown')
        .find('a')
    )
    assert 'Results 1-15 of 29 for polish workers in germany' in page.text()
    assert 'None' in page('.applied-filters').with_text('Trial').text()

    # test multiple facets
    page = follow_link(
        page('.facet')
        .with_text('Language')
        .find('p')
        .with_text('English')
        .find('a')
    )
    assert 'Results 1-15 of 24 for polish workers in germany' in page.text()
    assert 'None' in page('.applied-filters').with_text('Trial').text()
    assert 'English' in page('.applied-filters').with_text('Language').text()

    page = follow_link(
        page('.facet')
        .with_text('Source')
        .find('p')
        .with_text('Typescript')
        .find('a')
    )
    assert 'Results 1-4 of 4 for polish workers in germany' in page.text()
    assert 'None' in page('.applied-filters').with_text('Trial').text()
    assert 'English' in page('.applied-filters').with_text('Language').text()
    assert 'Typescript' in page('.applied-filters').with_text('Source').text()

    # test date range
    date_range = page('.facet').with_text('Date').find('form')
    from_name = date_range.find('input[type=number]').nth(0).attr('name')
    to_name = date_range.find('input[type=number]').nth(1).attr('name')
    page = go_to(date_range.submit_url({from_name: 1941, to_name: 1942}))
    assert 'Results 1-2 of 2 for polish workers in germany' in page.text()
    assert 'None' in page('.applied-filters').with_text('Trial').text()
    assert 'English' in page('.applied-filters').with_text('Language').text()
    assert 'Typescript' in page('.applied-filters').with_text('Source').text()
    assert '1941-1942' in page('.applied-filters').with_text('Date').text()
    assert '1941' in page('.document-row').text()
    assert '1942' in page('.document-row').text()

    # test removing all filters
    page = follow_link(page('a').with_text('Clear all filters'))
    assert 'Results 1-15 of 41 for polish workers in germany' in page.text()


def test_keyword_search(query):
    page = query('')
    search_bar = page('input[type="search"]')
    page = go_to(search_bar.submit_value('experiments'))

    assert 'Results 1-15 of 1522 for experiments' in page('p').text()
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
    def _count(q, count, page_count=None, first_count=None):
        page = query(q)
        if page_count == None:
            page_count = 15
        if first_count == None:
            first_count = 1
        assert (
            'Results {}-{} of {} for {}'.format(
                first_count, page_count, count, q
            )
            in page('.results-count').text()
        )

    return _count


def test_field_search(count_results):

    # TODO: these tests are pretty brittle to indexing changes, consider beefing them up
    count_results('workers', 780)
    count_results('workers author:fritz', 80)
    count_results('workers date:january', 32)
    count_results('workers -trial:(nmt 4)', 663)
    count_results('workers evidence:NO-190', 5, 5)
    count_results('workers source:typescript language:german', 37)
    count_results(
        'workers source:typescript language:german -author:Milch', 28
    )
    count_results('workers trial:(nmt 2 | nmt 4)', 263)
    count_results('workers date:unknown', 186)
    count_results('workers date:none', 186)
    count_results('workers -date:none', 598)
    count_results('workers -date:none notafield:(no matches)', 598)
    count_results('workers trial:(nmt 2 | nmt 4) author:speer|fritz', 37)
    count_results('workers author:"hitler adolf"', 0, 0, 0)
    count_results('workers author:"adolf hitler"', 11, 11)
    count_results('workers exhibit:prosecution', 170)
    count_results('* author:hitler -author:adolf', 0, 0, 0)
    count_results('* exhibit:handloser', 81)
    count_results('malaria', 100)
    count_results('freezing', 285)
    count_results('malaria freezing', 34)
    count_results('-malaria freezing', 254)
    count_results('malaria -freezing', 69)
    count_results('malaria | freezing', 349)


def test_document_search(query):
    page = query('workers')
    assert 'Results 1-15 of 780 for workers' in page.text()
    page = follow_link(
        page('.document-row a').with_text(
            'Instructions to employment offices concerning the replacement of Jewish workers in Germany'
        )
    )

    search_bar = page('input[type=search]')
    assert search_bar
    assert search_bar.val() == 'workers'

    page = go_to(search_bar.submit_value('instructions'))
    assert 'Results 1-15 of 722 for instructions' in page.text()

    q = 'instructions for air force medical'
    page = go_to(search_bar.submit_value(q))
    assert f'Results 1-3 of 3 for {q}' in page.text()
    page = follow_link(
        page('.document-row a').with_text(
            'Instructions for air force medical officers regarding freezing'
        )
    )

    search_bar = page('input[type=search]')
    assert search_bar
    assert search_bar.val() == q

    page = follow_link(page('a').with_text('Back to search results'))
    assert f'Results 1-3 of 3 for {q}' in page.text()


def test_landing_search(query):
    page = go_to(reverse('content:landing'))

    search_bar = page('input[type=search]')
    assert search_bar

    page = go_to(search_bar.submit_value('workers'))
    assert 'Results 1-15 of 780 for workers' in page.text()

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

    assert (
        'Results 1-7 of 7 for workers type:transcripts|photographs'
        in page.text()
    )


def test_transcript_snippets(query):
    page = query('documents type:transcript')

    assert 'Results 1-5 of 5 for documents type:transcript' in page.text()
    assert '4039 results in this transcript' in page.text()

    # snippets on several pages
    assert '... p. 8350' in page.text()
    assert '... p. 8963' in page.text()
    assert '... p. 144' in page.text()

    # test single page results
    page = query('documents hlsl:2')

    assert 'Results 1-1 of 1 for documents hlsl:2' in page.text()
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

    assert 'Results 1-15 of 14553 for *' in page.text()

    page = follow_link(page('a.page-number').with_text('971'))

    assert 'Results 14551-14553 of 14553 for *' in page.text()


def test_sort(query):
    # testing "relevance" might be too brittle for now
    page = query('experiments')
    assert 'Argument: Final plea for Karl Gebhardt' in page.text()

    page = follow_link(page('[data-test="search-result-last-page"]'))
    assert (
        'Brief: Prosecution closing brief against Georg Loerner' in page.text()
    )

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
    previous_to_last = int(last_page_link.text()) - 1
    page = follow_link(page('a.page-number').with_text(str(previous_to_last)))
    assert '492 pages' in page.text()
