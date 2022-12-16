import pytest

from nuremberg.search.forms import AdvancedDocumentSearchForm


pytestmark = pytest.mark.django_db


def test_advanced_search_form_errors():
    data = {
        'keywords': 'foo bar|baz',
        'title': 'Some Title',
        'author': 'Adolf Hitlerrrr',  # Not a valid author
        'defendant': 'Not a Defendant',  # Not a valid defendant
        'issue': 'A Trial Issue',  # Not a valid issue
        'trial': 'CASE',  # Not a valid trial
        'language': 'spanish',  # Not a valid lang
        'notes': 'A description',
        'source': 'Case in english',
    }
    form = AdvancedDocumentSearchForm(data)

    assert not form.is_valid()
    assert sorted(form.errors.keys()) == [
        'author',
        'defendant',
        'issue',
        'language',
        'trial',
    ]


def test_advanced_search_form_as_search_qs_simple():
    data = {
        'keywords': 'foo bar|baz',
        'title': 'Some Title',
        'author': 'Adolf Hitler',
        'defendant': 'Rose',
        'issue': 'A Trial Issue',
        'trial': 'IMT',
        'language': 'Croatian',
        'notes': 'A description',
        'source': 'Case in english',
    }
    form = AdvancedDocumentSearchForm()
    expected = (
        'keywords:"foo bar|baz" title:"Some Title" author:"Adolf Hitler" '
        'defendant:"Rose" issue:"A Trial Issue" trial:"IMT" '
        'language:"Croatian" notes:"A description" source:"Case in english"'
    )
    assert form.as_search_qs(data) == expected


def test_advanced_search_form_as_search_qs_cleaned_data():
    data = {
        'keywords': 'foo bar|baz',
        'title': 'Some Title',
        'author': 'Adolf Hitler',
        'defendant': 'Rose',
        'trial': 'IMT',
        'language': 'english',
        'notes': 'A description',
        'source': 'Case in english',
    }
    form = AdvancedDocumentSearchForm(data)

    assert form.is_valid(), form.errors
    expected = (
        'keywords:"foo bar|baz" title:"Some Title" author:"Adolf Hitler" '
        'defendant:"Rose" trial:"IMT" language:"english" '
        'notes:"A description" source:"Case in english"'
    )
    assert form.as_search_qs() == expected


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
