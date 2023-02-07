import datetime

import pytest
from model_bakery import baker
from django.urls import reverse
from django.utils.text import slugify

from nuremberg.documents.models import (
    Document,
    DocumentDate,
    DocumentPersonalAuthor,
    DocumentText,
    PersonalAuthorProperty,
)
from .helpers import (
    make_author,
    make_document,
    make_document_external_metadata,
    make_document_text,
)


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('year, month, day', [(2022, 2, 29), (2022, 4, 31)])
def test_document_date_invalid_date(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() is None


def test_document_date_valid_as_date():
    today = datetime.date.today()
    d = DocumentDate.objects.create(
        day=today.day, month=today.month, year=today.year
    )
    assert d.as_date() == today


def test_document_total_pages():
    doc = baker.make('Document')

    assert doc.total_pages == doc.image_count


def test_document_language_name():
    doc = baker.make('Document')
    assert doc.language_name == doc.language.name

    doc = baker.make('Document', language__name='Foo')
    assert doc.language_name == 'Foo'


def test_document_source_name():
    doc = baker.make('Document', source__name='foo')

    assert doc.source_name == 'foo'


def test_document_retrieve_full_text_empty():
    doc = baker.make('Document')

    assert doc.full_texts().count() == 0
    assert doc.full_text is None
    assert doc.text == ''


def test_document_retrieve_full_text_no_evidence_code_match():
    baker.make(
        'DocumentText', evidence_code_series='FF', evidence_code_num='123'
    )
    evidence_codes = ['FF-12', 'Z-123']
    doc = make_document(evidence_codes=evidence_codes)

    assert doc.full_texts().count() == 0
    assert doc.full_text is None
    assert doc.text == ''


def test_document_retrieve_full_text_real_729():
    for doc_id in [30, 3058, 2539, 451438]:
        doc = Document.objects.get(id=doc_id)

        result = doc.full_texts()

        assert result.count() == 1

        result = result.get()
        assert isinstance(result, DocumentText)
        assert result.id == 729
        assert doc.full_text == result
        assert doc.text == result.text


def test_document_retrieve_full_text_real_473():
    docs = [
        49,
        58,
        1437,
        3067,
        3107,
        2442,
        2443,
        2445,
        2447,
        2444,
        2446,
        451403,
        452253,
        452353,
    ]
    for doc_id in docs:
        doc = Document.objects.get(id=doc_id)

        result = doc.full_texts()

        assert result.count() == 1

        result = result.get()
        assert isinstance(result, DocumentText)
        assert result.id == 473
        assert doc.full_text == result
        assert doc.text == result.text


def test_document_citations_zero():
    doc = baker.make('Document')

    assert doc.citations.all().count() == 0


def test_document_citations_transcrip_does_not_exist():
    doc = baker.make('Document')
    citation = baker.make('DocumentCitation', document=doc)

    assert citation.case is not None
    assert getattr(citation.case, 'transcript', None) is None
    assert doc.citations.all().count() == 1
    assert doc.citations.get().transcript_link is None


def test_document_citations_transcrip_link_none():
    doc = baker.make('Document')
    citation = baker.make(
        'DocumentCitation',
        document=doc,
        transcript_seq_number=0,
        transcript_page_number=42,
    )
    transcript = baker.make('Transcript', case=citation.case)

    assert citation.case is not None
    assert getattr(citation.case, 'transcript', None) is transcript
    assert doc.citations.all().count() == 1
    assert doc.citations.get().transcript_link is None


def test_document_citations_transcrip_link_page_number():
    doc = baker.make('Document')
    citation = baker.make(
        'DocumentCitation',
        document=doc,
        transcript_seq_number=None,
        transcript_page_number=42,
    )
    transcript = baker.make('Transcript', case=citation.case)

    assert citation.case is not None
    assert getattr(citation.case, 'transcript', None) is transcript
    assert doc.citations.all().count() == 1
    assert (
        doc.citations.get().transcript_link
        == reverse('transcripts:show', args=(transcript.id,)) + '?page=42'
    )


def test_document_citations_transcrip_link_seq_number():
    doc = baker.make('Document')
    citation = baker.make(
        'DocumentCitation',
        document=doc,
        transcript_seq_number=230,
        transcript_page_number=42,
    )
    transcript = baker.make('Transcript', case=citation.case)

    assert citation.case is not None
    assert getattr(citation.case, 'transcript', None) is transcript
    assert doc.citations.all().count() == 1
    assert (
        doc.citations.get().transcript_link
        == reverse('transcripts:show', args=(transcript.id,)) + '?seq=230'
    )


def test_document_retrieve_external_metadata_empty():
    doc = baker.make('Document')

    assert doc.external_metadata().count() == 0


def test_document_retrieve_external_metadata_no_evidence_code_match():
    baker.make(
        'DocumentExternalMetadata',
        evidence_code_series='FF',
        evidence_code_num='123',
    )
    evidence_codes = ['FF-12', 'Z-123']
    doc = make_document(evidence_codes=evidence_codes)

    assert doc.external_metadata().count() == 0


def test_document_retrieve_external_metadata_evidence_code_match():
    baker.make(
        'DocumentExternalMetadata',
        evidence_code_series='FF',
        evidence_code_num='123',
    )
    e = baker.make(
        'DocumentExternalMetadata',
        evidence_code_series='FF',
        evidence_code_num='123',
        evidence_code_suffix='a',
    )
    evidence_codes = ['FF-12', 'Z-123', 'FF-123a']
    doc = make_document(evidence_codes=evidence_codes)

    assert doc.external_metadata().count() == 1
    assert doc.external_metadata().get() == e


def test_document_retrieve_external_metadata(django_assert_num_queries):
    codes = ['AAAA-123456', 'BBBB-456789', 'CCCC-9876543210']
    doc = make_document(evidence_codes=codes)

    expected = [
        make_document_external_metadata(evidence_code=code) for code in codes
    ]

    # none of the following have an evidence code match
    make_document_external_metadata(evidence_code='CCCC-987654321')
    make_document_external_metadata(evidence_code='BBBB-123456')
    make_document_external_metadata(evidence_code='AAAA-456789')
    make_document_external_metadata(evidence_code='AAA-123456')

    result = doc.external_metadata().order_by('id')

    with django_assert_num_queries(1):
        assert list(map(str, result)) == [str(e) for e in expected]


def test_document_retrieve_external_metadata_order(django_assert_num_queries):
    code = 'PS-123456789'
    doc = make_document(evidence_codes=[code])

    sources = [
        baker.make(
            'DocumentExternalMetadataSource', name=f'Source {i}', priority=i
        )
        for i in range(3)
    ]
    expected = [
        make_document_external_metadata(evidence_code=code, source=source)
        for source in sources  # priorities sort lower -> higher
    ]

    result = doc.external_metadata()

    with django_assert_num_queries(1):
        assert list(map(str, result)) == [str(e) for e in expected]


def test_author_slug_full_name():
    author = make_author(
        first_name='First Name: So Many #$ different Characters! ♡',
        last_name=' Last ↦ Name',
        title='Some Title',
    )

    assert author.slug == 'first-name-so-many-different-characters-last-name'


def test_author_slug_no_first_name():
    author = make_author(
        first_name='',
        last_name='Only Last Name',
        title='Some Title',
    )

    assert author.slug == 'only-last-name'


def test_author_slug_no_last_name():
    author = make_author(
        first_name='Only First Name',
        last_name='',
        title='Some Title',
    )

    assert author.slug == 'only-first-name'


def test_author_properties_no_author():
    last_id = DocumentPersonalAuthor.objects.all().order_by('id').last().id
    empty_qs = DocumentPersonalAuthor.objects.filter(id=last_id + 1)

    assert empty_qs.count() == 0
    assert empty_qs.metadata() == []


def test_author_properties_minimal_result(django_assert_num_queries):
    author = make_author()

    with django_assert_num_queries(1):  # check for DocumentAuthorExtra
        result = author.metadata(minimal=True)

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
    }


def test_author_properties_no_property_match_uses_title():
    author = make_author(
        first_name='No',
        last_name='Properties',
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_title_even_if_empty_first_name():
    author = make_author(
        first_name='Does Not Exist',
        last_name=None,
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_title_even_if_empty_last_name():
    author = make_author(
        first_name=None,
        last_name='Does Not Exist',
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_no_property_match_empty_title():
    author = make_author(
        first_name='Does Not',
        last_name='Exist',
        title='',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': '',
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_property_ranks():
    author = make_author(first_name='Some', last_name='Name')

    rank0 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank 0', rank=0
    )
    prop0 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank0.name,
        value='Ignored 0',
    )
    assert prop0.rank == 0

    rank_negative_1 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank -1', rank=-1
    )
    prop_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_negative_1.name,
        value='Ignored -1',
    )
    assert prop_1.rank == -1

    prop_none = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name='no rank available',
        value='Ignored None',
    )
    assert prop_none.rank is None

    rank_1 = baker.make('PersonalAuthorPropertyRank', name='valid 1', rank=1)
    prop_1_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_1.name,
        value='one value',
        qualifier='',
        qualifier_value='',
    )
    assert prop_1_1.rank == 1
    prop_1_2 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_1.name,
        value='another',
        qualifier='',
        qualifier_value='',
    )
    assert prop_1_2.rank == 1

    rank_5 = baker.make('PersonalAuthorPropertyRank', name='valid 5', rank=5)
    prop_5 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_5.name,
        value='different value, could be a link',
        qualifier='',
        qualifier_value='',
    )
    assert prop_5.rank == 5

    result = author.metadata()

    # order is given by higher rank first, then value
    expected = [
        {
            'rank': 5,
            'name': 'valid 5',
            'prop_values': [{'value': prop_5.value, 'qualifiers': []}],
        },
        {
            'rank': 1,
            'name': 'valid 1',
            'prop_values': [
                {'value': 'another', 'qualifiers': []},
                {'value': 'one value', 'qualifiers': []},
            ],
        },
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_1_1.personal_author_description,
            'wikidata_name': prop_1_1.personal_author_name,
        },
        'image': None,
        'properties': expected,
    }


def test_author_properties_groups_qualifiers(django_assert_num_queries):
    author = make_author()

    rank = baker.make('PersonalAuthorPropertyRank', name='a property', rank=10)
    first = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='country',
        qualifier_value='US',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='country',
        qualifier_value='CA',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='another value',  # should not group with previous qualifier
        qualifier='country',
        qualifier_value='ES',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='county',  # different spelling but same qualifier
        qualifier_value='Village',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='subject has role',  # should be replaced by 'role'
        qualifier_value='role 1',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='object has role',  # should be replaced by 'role'
        qualifier_value='role 2',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='role',
        qualifier_value='other role',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank.name,
        value='some value',
        qualifier='valid in place',  # should be ignored
        qualifier_value='ignored',
    )

    # first fetch DocumentAuthorExtra, then fetch ranks and properties
    with django_assert_num_queries(3):
        result = author.metadata()

    # order is given by higher rank first, then value
    expected = [
        {
            'rank': 10,
            'name': 'a property',
            'prop_values': [
                {
                    'value': 'another value',
                    'qualifiers': [('country', ['ES'])],
                },
                {
                    'value': 'some value',
                    'qualifiers': [
                        ('country', ['CA', 'US']),
                        ('county', ['Village']),
                        ('role', ['other role', 'role 1', 'role 2']),
                    ],
                },
            ],
        },
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': first.personal_author_description,
            'wikidata_name': first.personal_author_name,
        },
        'image': None,
        'properties': expected,
    }


def test_author_properties_extracts_image():
    author = make_author(
        first_name='Some Other',
        last_name='Name',
        title='Sir Someone',
    )

    rank_image = baker.make(
        'PersonalAuthorPropertyRank', name='image', rank=30
    )
    prop_image_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-1.jpg',
        qualifier='',
        qualifier_value='',
    )
    assert prop_image_1.rank == 30
    prop_image_2 = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-2.jpg',
        qualifier='',
        qualifier_value='',
    )
    assert prop_image_2.rank == 30

    result = author.metadata()

    # Default alt if no 'media legend' qualifier is present
    image = {
        'url': prop_image_1.value,
        'alt': f'Image of {author.full_name()}',
    }
    author_data = {
        'name': author.full_name(),
        'id': author.id,
        'slug': author.slug,
        'title': author.title,
        'description': prop_image_1.personal_author_description,
        'wikidata_name': prop_image_1.personal_author_name,
    }
    assert result == {
        'author': author_data,
        'image': image,
        'properties': [],
    }

    # now define 'media legend' for the second image, it will not be used
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-2.jpg',
        qualifier='media legend',
        qualifier_value='The Legend for Image 2',
    )

    result = author.metadata()
    assert result == {
        'author': author_data,
        'image': image,
        'properties': [],
    }

    # now define 'media legend' for the first image, it should be picked up
    legend = 'The Legend for Image 1'
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-1.jpg',
        qualifier='media legend',
        qualifier_value=legend,
    )

    result = author.metadata()

    image['alt'] = legend
    assert result == {
        'author': author_data,
        'image': image,
        'properties': [],
    }


def test_author_properties_groups_birth_data():
    author = make_author()

    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=24
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=23
    )
    prop_place_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='',
        qualifier_value='',
    )
    prop_date_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )

    result = author.metadata()

    born = f'{prop_date_of_birth.value} ({prop_place_of_birth.value})'
    properties = [
        {
            'rank': 24,
            'name': 'born',
            'prop_values': [{'value': born, 'qualifiers': []}],
        }
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_place_of_birth.personal_author_description,
            'wikidata_name': prop_place_of_birth.personal_author_name,
        },
        'image': None,
        'properties': properties,
    }


def test_author_properties_groups_death_data():
    author = make_author()

    rank_place_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='place of death', rank=24
    )
    rank_date_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='date of death', rank=23
    )
    prop_place_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='A city or location',
        qualifier='',
        qualifier_value='',
    )
    prop_date_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )

    result = author.metadata()

    died = f'{prop_date_of_death.value} ({prop_place_of_death.value})'
    properties = [
        {
            'rank': 24,
            'name': 'died',
            'prop_values': [{'value': died, 'qualifiers': []}],
        }
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_place_of_death.personal_author_description,
            'wikidata_name': prop_place_of_death.personal_author_name,
        },
        'image': None,
        'properties': properties,
    }


def test_author_properties_name_data_ignored():
    author = make_author(
        first_name='John',
        last_name='Doe',
    )
    rank_family_name = baker.make(
        'PersonalAuthorPropertyRank', name='family name', rank=28
    )
    rank_given_name = baker.make(
        'PersonalAuthorPropertyRank', name='given name', rank=27
    )
    rank_birth_name = baker.make(
        'PersonalAuthorPropertyRank', name='birth name', rank=26
    )
    first = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_family_name.name,
        value='Family Name',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_given_name.name,
        value='Given Name',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_birth_name.name,
        value='Birth Name',
    )

    result = author.metadata()

    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': first.personal_author_description,
            'wikidata_name': first.personal_author_name,
        },
        'image': None,
        'properties': [],
    }


def test_author_properties_dates_and_qualifiers():
    author = make_author()

    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=26
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=25
    )
    rank_place_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='place of death', rank=24
    )
    rank_date_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='date of death', rank=23
    )

    prop_place_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='country',
        qualifier_value='DE',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='country',
        qualifier_value='Austria-Hungary',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
        qualifier='stress address',
        qualifier_value='Some Address',
    )

    prop_date_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='country',
        qualifier_value='Bulgaria',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='child of',
        qualifier_value='Parent Name 1',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='child of',
        qualifier_value='Parent Name 2',
    )

    prop_place_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='Another city',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='Another city',
        qualifier='country',
        qualifier_value='Nazi Germany',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_place_of_death.name,
        value='Another city',
        qualifier='located in the administrative territorial entity',
        qualifier_value='Berlin',
    )

    prop_date_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='cause',
        qualifier_value='poisoning',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='something',
        qualifier_value='one value',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_date_of_death.name,
        value='1999-01-01',
        qualifier='something',
        qualifier_value='another value',
    )

    result = author.metadata()

    born = f'{prop_date_of_birth.value} ({prop_place_of_birth.value})'
    died = f'{prop_date_of_death.value} ({prop_place_of_death.value})'
    properties = [
        {
            'rank': 26,
            'name': 'born',
            'prop_values': [
                {
                    'value': born,
                    'qualifiers': [
                        ('child of', ['Parent Name 1', 'Parent Name 2']),
                        ('country', ['Austria-Hungary', 'Bulgaria', 'DE']),
                        ('stress address', ['Some Address']),
                    ],
                }
            ],
        },
        {
            'rank': 24,
            'name': 'died',
            'prop_values': [
                {
                    'value': died,
                    'qualifiers': [
                        ('cause', ['poisoning']),
                        ('country', ['Nazi Germany']),
                        (
                            'located in the administrative territorial entity',
                            ['Berlin'],
                        ),
                        ('something', ['another value', 'one value']),
                    ],
                }
            ],
        },
    ]
    assert result == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': prop_place_of_birth.personal_author_description,
            'wikidata_name': prop_place_of_birth.personal_author_name,
        },
        'image': None,
        'properties': properties,
    }


def test_author_extra_as_dict():
    author = make_author()
    extra = baker.make('DocumentAuthorExtra', author=author, properties=[])

    result = extra.as_dict()

    assert result == {
        'author': {
            'name': extra.name,
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': extra.description,
        },
        'image': None,
        'properties': [],
    }


def test_author_extra_as_dict_with_image():
    author = make_author()
    image_path = 'some-path-for-the-image'
    extra = baker.make(
        'DocumentAuthorExtra', author=author, properties=[], image=image_path
    )

    result = extra.as_dict()

    assert result == {
        'author': {
            'name': extra.name,
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': extra.description,
        },
        'image': {'url': f'/media/{image_path}', 'alt': extra.image_alt},
        'properties': [],
    }


def test_author_extra_as_dict_minimal():
    author = make_author()
    extra = baker.make('DocumentAuthorExtra', author=author)

    result = extra.as_dict(minimal=True)

    assert result == {
        'author': {
            'name': extra.name,
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': extra.description,
        }
    }


def test_document_exhibit_code_book_code_none():
    exhibit = baker.make('DocumentExhibitCode')

    assert exhibit.book_code is None


def test_document_exhibit_code_book_code_prosecution():
    exhibit = baker.make('DocumentExhibitCode', prosecution_doc_book_number=3)

    assert exhibit.book_code == 'Prosecution 3'


def test_document_exhibit_code_book_code_defendant_name():
    exhibit = baker.make(
        'DocumentExhibitCode',
        defense_doc_book_number=42,
        defense_name__name='Last Name',
        defense_name_denormalized='Other Name',
    )
    assert exhibit.defense_name is not None
    assert bool(exhibit.defense_name.name)
    assert exhibit.book_code == 'Last Name 42'

    del exhibit.book_code
    exhibit.defense_name = None
    assert exhibit.book_code == 'Other Name 42'

    del exhibit.book_code
    exhibit.defense_name_denormalized = ''
    assert exhibit.book_code == 'Defendant 42'


def test_document_text_evidence_code():
    doc_text = baker.make(
        'DocumentText',
        evidence_code_series='FF',
        evidence_code_num='123-85-X',
        evidence_code_tag='Not relevant',
    )

    assert doc_text.evidence_code == 'FF-123-85-X'


def test_document_text_language_name():
    doc_text = baker.make('DocumentText')

    assert doc_text.language_name == 'English'


def test_document_text_slug():
    doc_text = baker.make(
        'DocumentText',
        title='Something & Something/ELSE !@#',
    )

    assert doc_text.slug == 'something-somethingelse'


def test_document_text_source_name():
    doc_text = baker.make(
        'DocumentText',
        source_citation='Lorem ipsum dolor sit amet, consectetur adipiscing.',
    )

    assert doc_text.source_name == doc_text.source_citation


def test_document_text_total_pages_text_none():
    doc_text = baker.make('DocumentText', text=None)
    assert doc_text.total_pages == 0


def test_document_text_total_pages_empty_text():
    doc_text = baker.make('DocumentText', text='')

    assert doc_text.total_pages == 0


def test_document_text_total_pages():
    doc_text = baker.make(
        'DocumentText',
        evidence_code_series='XY',
        evidence_code_num='456',
        evidence_code_tag='123-AZ',
        text='Something',
    )

    assert doc_text.total_pages == 1

    doc_text.text = (
        'Lorem ipsum dolor sit amet, 123-AZ consectetur adipiscing elit. '
        'Praesent laoreet purus quis imperdiet gravida. '
        'Ut viverra mi eget tortor iaculis elementum. '
        'Phasellus semper rutrum mattis. Morbi nec vehicula diam. '
        'Mauris rutrum consequat augue a vehicula. Fusce vitae lacus ipsum.'
    )
    del doc_text.total_pages  # invalidate cached property
    assert doc_text.total_pages == 2

    doc_text.text = (
        'Lorem ipsum dolor sit amet, consectetur adipiscing elit. 123-AZ'
        'Praesent laoreet purus quis imperdiet gravida. 123-AZ'
        'Ut viverra mi eget tortor iaculis elementum. 123-AZ'
        'Phasellus semper rutrum mattis. Morbi nec vehicula diam. 123-AZ'
        'Mauris rutrum consequat augue a vehicula. Fusce vitae lacus ipsum.'
    )
    del doc_text.total_pages  # invalidate cached property
    assert doc_text.total_pages == 5

    doc_text.text = (
        'Lorem ipsum dolor sit amet, consectetur adipiscing elit. 123-AZ'
        'Praesent laoreet purus quis imperdiet gravida. 123-AZ'
        'Ut viverra mi eget tortor iaculis elementum. 123—AZ'  # an emdash
        'Phasellus semper rutrum mattis. Morbi nec vehicula diam. 123-AZ'
        'Mauris rutrum consequat augue a vehicula. Fusce vitae lacus ipsum.'
    )
    del doc_text.total_pages  # invalidate cached property
    assert doc_text.total_pages == 5


def test_document_text_retrieve_documents_empty():
    doc_text = baker.make(
        'DocumentText', evidence_code_series='FF', evidence_code_num='123'
    )

    assert doc_text.documents().count() == 0
    assert doc_text.document is None
    assert doc_text.slug == slugify(doc_text.title)


def test_document_text_retrieve_documents_no_evidence_code_match():
    doc_text = baker.make(
        'DocumentText', evidence_code_series='FF', evidence_code_num='123'
    )
    make_document(evidence_codes=['Z-123', 'FF-12'])

    assert doc_text.documents().count() == 0
    assert doc_text.document is None
    assert doc_text.slug == slugify(doc_text.title)


def test_document_text_retrieve_documents_simple():
    doc_text = baker.make(
        'DocumentText',
        evidence_code_series='FF',
        evidence_code_num='123',
        evidence_code_tag='Not relevant',
    )
    evidence_codes = ['Z-123', 'FF-123']
    doc = make_document(evidence_codes=evidence_codes)

    result = doc_text.documents()

    assert result.count() == 1
    assert result.get() == doc
    assert doc_text.document == doc


def test_document_text_retrieve_documents_proper_evidence_code_matching():
    doc_text = baker.make(
        'DocumentText',
        evidence_code_series='FF',
        evidence_code_num='123',
        evidence_code_tag='Not relevant',
    )
    make_document(evidence_codes=['Z-123'])
    make_document(evidence_codes=['FF-12'])

    result = doc_text.documents()

    assert result.count() == 0


def test_document_text_retrieve_documents_evidence_code_not_number():
    doc_text = baker.make(
        'DocumentText',
        evidence_code_series='FF',
        evidence_code_num='407-IX',
    )

    result = doc_text.documents()

    assert result.count() == 0
    assert doc_text.document is None


def test_document_text_retrieve_documents_real_729():
    doc_text_729 = DocumentText.objects.get(id=729)

    result = doc_text_729.documents()

    # Document 2539 has no exhibit code, the other two have 1 exhibit each.
    # But document 451438 was used in trial IMT, while docuemtn 30 was used in
    # trial NMT 1 and document 3058 in NMT 2
    expected_docs = [451438, 30, 3058, 2539]
    assert [d.id for d in result] == expected_docs
    assert doc_text_729.document == Document.objects.get(id=expected_docs[0])


def test_document_text_retrieve_documents_real_473():
    doc_text_473 = DocumentText.objects.get(id=473)

    result = doc_text_473.documents()

    # Documents 2442 to 24465 have no exhibit code.
    # All remaining have the same source (Case Files/English), but 3067 and
    # 3107 were used in a trial case with lower score than the rest (NMT 2).
    # The same happens with 49, 58 and 1437 that were used in trial NMT 1, but
    # then 451403, 452253 and 452353 all were used in trial IMT which has the
    # top priority among trials -- so they all end up with the same score...
    # we need to break that tie.
    expected_docs = [
        451403,
        452253,
        452353,
        49,
        58,
        1437,
        3067,
        3107,
        2442,
        2443,
        2445,
        2447,
        2444,
        2446,
    ]
    assert [d.id for d in result] == expected_docs
    assert doc_text_473.document == Document.objects.get(id=expected_docs[0])


def test_document_text_no_matching_documents(django_assert_num_queries):
    last_text_id = DocumentText.objects.all().order_by('id').last().id

    items = [
        [],
        ['AAAA-123456'],
        ['AAAA-123456', 'BBBB-456789'],
        ['BBBB-456789'],
        ['CCCC-9876543210'],
    ]
    for codes in items:
        make_document(evidence_codes=codes)
        for code in codes:
            make_document_text(evidence_code=code)

    # none has an evidence code match; also the `tag` is ignored
    expected = [
        make_document_text(evidence_code='CCCC-987654321'),
        make_document_text(evidence_code='BBBB-123456'),
        make_document_text(evidence_code='AAAA-456789'),
        make_document_text(evidence_code='AAA-123456'),
        make_document_text(evidence_code_tag='AAAA-123456'),
    ]

    # Given that tests are using the real DB, we need to craft a query which
    # would operate over the instances baked for this test only.
    result = DocumentText.objects.filter(
        id__gt=last_text_id
    ).no_matching_document()

    assert result.count() == len(expected)
    with django_assert_num_queries(1):
        assert list(result) == expected
