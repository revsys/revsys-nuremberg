import pytest

from nuremberg.search.forms import (
    AdvancedDocumentSearchForm,
    FieldedSearchForm,
)
from nuremberg.search.lib.solr_grouping_backend import GroupedSearchQuerySet


pytestmark = pytest.mark.django_db


form_cases = [
    (None, False),
    ('', False),
    ('type:document', False),
    ('hitler', True),
    ('hitler type:document', True),
    ('type:document hitler', True),
    ('hitler type:document "freezing experiments" year:1940', True),
    ('type:document "freezing experiments" year:1940', True),
    ('type:document year:1940', False),
]


@pytest.mark.parametrize('q, expected', form_cases)
def test_search_form_has_keyword_search(q, expected):
    if q is None:
        data = {}
    else:
        data = {'q': q}
    queryset = GroupedSearchQuerySet()
    form = FieldedSearchForm(data=data, searchqueryset=queryset)
    assert form.is_valid(), form.errors
    form.search()
    assert form.has_keyword_search is expected


def test_advanced_search_form_errors():
    data = {
        'keywords': 'foo bar|baz',
        'title': 'Some Title',
        'author': ['Adolf Hitlerrrr'],  # Not a valid author
        'defendant': 'Not a Defendant',  # Not a valid defendant
        'issue': 'A Trial Issue',  # Not a valid issue
        'trial': 'CASE',  # Not a valid trial
        'language': 'spanish',  # Not a valid lang
        'notes': 'A description',
        'source': 'Case in english',  # Not a valid source
    }
    form = AdvancedDocumentSearchForm(data)

    assert not form.is_valid()
    assert sorted(form.errors.keys()) == [
        'author',
        'defendant',
        'issue',
        'language',
        'source',
        'trial',
    ]


def test_advanced_search_form_as_search_qs_simple():
    data = {
        'keywords': 'foo bar|baz',
        'title': 'Some Title',
        'author': ['Adolf Hitler'],
        'defendant': 'Rose',
        'issue': 'A Trial Issue',
        'trial': 'IMT',
        'language': 'Croatian',
        'notes': 'something',
        'source': 'Photostat',
    }
    form = AdvancedDocumentSearchForm()
    expected = (
        'keywords:foo keywords:bar|baz title:Some title:Title notes:something '
        'author:"Adolf Hitler" defendant:"Rose" '
        'issue:"A Trial Issue" trial:"IMT" '
        'language:"Croatian" source:"Photostat"'
    )
    assert form.as_search_qs(data) == expected


def test_advanced_search_form_as_search_qs_author_list():
    data = {
        'keywords': 'foo bar|baz',
        'title': 'Some Title',
        'author': ['Adolf Hitler', 'Karl Weiss'],
        'defendant': 'Rose',
        'issue': 'A Trial Issue',
        'trial': 'IMT',
        'language': 'Croatian',
        'notes': 'something',
        'source': 'Photostat',
    }
    form = AdvancedDocumentSearchForm()
    expected = (
        'keywords:foo keywords:bar|baz title:Some title:Title notes:something '
        'author:"Adolf Hitler" author:"Karl Weiss" '
        'defendant:"Rose" '
        'issue:"A Trial Issue" trial:"IMT" '
        'language:"Croatian" source:"Photostat"'
    )
    assert form.as_search_qs(data) == expected


def test_advanced_search_form_as_search_qs_cleaned_data():
    data = {
        'keywords': 'bar|baz',
        'title': 'Some Title',
        'author': ['Adolf Hitler'],
        'defendant': 'Rose',
        'trial': 'IMT',
        'language': 'english',
        'notes': 'description',
        'source': 'Photostat',
    }
    form = AdvancedDocumentSearchForm(data)

    assert form.is_valid(), form.errors
    expected = (
        'keywords:bar|baz title:Some title:Title notes:description '
        'author:"Adolf Hitler" defendant:"Rose" '
        'trial:"IMT" language:"english" source:"Photostat"'
    )
    assert form.as_search_qs() == expected


def test_advanced_search_form_as_search_qs_year_range():
    data = {'year_range_start': ''}
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    assert form.as_search_qs() == ''

    data['year_range_start'] = '1948'
    form = AdvancedDocumentSearchForm(data)
    error = (
        'You must enter a to and a from year.  If you wish to search within a '
        'single year, please just duplicate the value.')
    assert not form.is_valid()
    assert form.errors == {'year_range': [error]}

    data['year_range_end'] = '1948'  # start was already set to 1948
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    assert form.as_search_qs() == 'date:1948'

    data['year_range_start'] = '1940'
    data['year_range_end'] = '1945'
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    assert form.as_search_qs() == 'date:1940|1941|1942|1943|1944|1945'

    # invalid value for an int
    data = {'year_range_start': 'PS'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['year_range']

    # invalid value for an int
    data = {'year_range_end': 'not a number'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['year_range']


def test_advanced_search_form_as_search_qs_evidence():
    data = {
        'evidence': 'PS',
        'evidence_num': '258',
    }
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    expected = 'evidence:"PS-258"'
    assert form.as_search_qs() == expected

    # now with a suffix
    data['evidence_suffix'] = 'A'
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    expected = 'evidence:"PS-258A"'
    assert form.as_search_qs() == expected

    # invalid data, missing evidence_num
    data = {'evidence': 'PS'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['evidence']

    # invalid data, missing evidence code
    data = {'evidence_num': '1062'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['evidence']


def test_advanced_search_form_as_search_qs_exhibit():
    data = {
        'exhibit': 'Prosecution',
        'exhibit_num': '258',
    }
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    expected = 'exhibit:"Prosecution 258"'
    assert form.as_search_qs() == expected

    # invalid data, missing exhibit_num
    data = {'exhibit': 'Rose'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['exhibit']

    # invalid data, missing exhibit code
    data = {'exhibit_num': '3'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['exhibit']


def test_advanced_search_form_as_search_qs_book():
    data = {
        'book': 'Prosecution',
        'book_num': '258',
    }
    form = AdvancedDocumentSearchForm(data)
    assert form.is_valid(), form.errors

    expected = 'book:"Prosecution 258"'
    assert form.as_search_qs() == expected

    # invalid data, missing book_num
    data = {'book': 'Rose'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['book']

    # invalid data, missing book code
    data = {'book_num': '3'}
    form = AdvancedDocumentSearchForm(data)
    assert not form.is_valid()
    assert sorted(form.errors.keys()) == ['book']


def test_advanced_search_form_from_search_qs_no_regex_match():
    q = ''
    form = AdvancedDocumentSearchForm.from_search_qs(q)

    assert form.is_valid(), form.errors
    for field in form:
        assert field.value() is None
