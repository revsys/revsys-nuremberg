import datetime
from functools import partial

import pytest
from model_bakery import baker

from nuremberg.documents.models import (
    DocumentDate,
    DocumentPersonalAuthor,
    PersonalAuthorProperty,
)
from .helpers import make_author


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('day', [None, 0, 33, -1])
@pytest.mark.parametrize('month', [None, 0, 13, -1])
@pytest.mark.parametrize('year', [None, 0, -1])
def test_document_date_invalid_date_params(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() is None


@pytest.mark.parametrize('year, month, day', [(2022, 2, 29), (2022, 4, 31)])
def test_document_date_invalid_date(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() is None


@pytest.mark.parametrize('day', [1, 30])
@pytest.mark.parametrize('month', [1, 12])
@pytest.mark.parametrize('year', [1, 1000, 2050])
def test_document_date_valid_as_date(day, month, year):
    d = DocumentDate.objects.create(day=day, month=month, year=year)
    assert d.as_date() == datetime.date(year, month, day)


# no qualifiers for now
make_property = partial(
    baker.make, 'PersonalAuthorProperty', qualifier='', qualifier_value=''
)


def test_author_properties_no_match():
    name = 'Does Not Exist'

    result = DocumentPersonalAuthor.objects.properties(name)

    assert result == {
        'author': {'name': name},
        'image': None,
        'properties': [],
    }


def test_author_properties_no_property_match_uses_title():
    name = 'No Properties'
    author = make_author(
        first_name='No',
        last_name='Properties',
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = DocumentPersonalAuthor.objects.properties(name)

    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_title_even_if_empty_first_name():
    name = 'Does Not Exist'
    author = make_author(
        first_name='Does Not Exist',
        last_name=None,
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = DocumentPersonalAuthor.objects.properties(name)

    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_title_even_if_empty_last_name():
    name = 'Does Not Exist'
    author = make_author(
        first_name=None,
        last_name='Does Not Exist',
        title='Some Title',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = DocumentPersonalAuthor.objects.properties(name)

    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': [],
    }


def test_author_properties_no_property_match_empty_title():
    name = 'Does Not Exist'
    author = make_author(
        first_name='Does Not',
        last_name='Exist',
        title='',
    )
    assert (
        PersonalAuthorProperty.objects.filter(personal_author=author).count()
        == 0
    )

    result = DocumentPersonalAuthor.objects.properties(name)

    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': [],
    }


def test_author_properties_uses_property_ranks():
    author = make_author(first_name='Some', last_name='Name')
    name = author.full_name()

    rank0 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank 0', rank=0
    )
    prop0 = make_property(
        personal_author=author,
        name=rank0.name,
        value='Ignored 0',
    )
    assert prop0.rank == 0

    rank_negative_1 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank -1', rank=-1
    )
    prop_1 = make_property(
        personal_author=author,
        name=rank_negative_1.name,
        value='Ignored -1',
    )
    assert prop_1.rank == -1

    prop_none = make_property(
        personal_author=author,
        name='no rank available',
        value='Ignored None',
    )
    assert prop_none.rank is None

    rank_1 = baker.make('PersonalAuthorPropertyRank', name='valid 1', rank=1)
    prop_1_1 = make_property(
        personal_author=author,
        name=rank_1.name,
        value='one value',
    )
    assert prop_1_1.rank == 1
    prop_1_2 = make_property(
        personal_author=author,
        name=rank_1.name,
        value='another',
    )
    assert prop_1_2.rank == 1

    rank_5 = baker.make('PersonalAuthorPropertyRank', name='valid 5', rank=5)
    prop_5 = make_property(
        personal_author=author,
        name=rank_5.name,
        value='different value, could be a link',
    )
    assert prop_5.rank == 5

    result = DocumentPersonalAuthor.objects.properties(name)

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
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': expected,
    }


def test_author_properties_extracts_image():
    author = make_author(
        first_name='Some Other',
        last_name='Name',
        title='Sir Someone',
    )
    name = author.full_name()

    rank_image = baker.make(
        'PersonalAuthorPropertyRank', name='image', rank=30
    )
    prop_image_1 = make_property(
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-1.jpg',
    )
    assert prop_image_1.rank == 30
    prop_image_2 = make_property(
        personal_author=author,
        name=rank_image.name,
        value='https://link-to-image-2.jpg',
    )
    assert prop_image_2.rank == 30

    result = DocumentPersonalAuthor.objects.properties(name)

    # XXX: alt needs data definition, waiting on Paul for this
    image = {'url': prop_image_1.value, 'alt': f'Image of {name}'}
    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': image,
        'properties': [],
    }


def test_author_properties_groups_birth_data():
    name = 'John Doe'
    author = make_author(
        first_name=name,
        last_name=None,
    )
    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=24
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=23
    )
    prop_place_of_birth = make_property(
        personal_author=author,
        name=rank_place_of_birth.name,
        value='A city or location',
    )
    prop_date_of_birth = make_property(
        personal_author=author,
        name=rank_date_of_birth.name,
        value='1979-01-01',
    )

    result = DocumentPersonalAuthor.objects.properties(name)

    born = f'{prop_date_of_birth.value} ({prop_place_of_birth.value})'
    properties = [
        {
            'rank': 24,
            'name': 'born',
            'prop_values': [{'value': born, 'qualifiers': []}],
        }
    ]
    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': properties,
    }


def test_author_properties_groups_death_data():
    name = 'John Doe'
    author = make_author(
        first_name=None,
        last_name=name,
    )
    rank_place_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='place of death', rank=24
    )
    rank_date_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='date of death', rank=23
    )
    prop_place_of_death = make_property(
        personal_author=author,
        name=rank_place_of_death.name,
        value='A city or location',
    )
    prop_date_of_death = make_property(
        personal_author=author,
        name=rank_date_of_death.name,
        value='1979-01-01',
    )

    result = DocumentPersonalAuthor.objects.properties(name)

    died = f'{prop_date_of_death.value} ({prop_place_of_death.value})'
    properties = [
        {
            'rank': 24,
            'name': 'died',
            'prop_values': [{'value': died, 'qualifiers': []}],
        }
    ]
    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': properties,
    }


def test_author_properties_name_data_ignored():
    name = 'John Doe'
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
    baker.make(
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

    result = DocumentPersonalAuthor.objects.properties(name)

    assert result == {
        'author': {'name': name, 'id': author.id, 'title': author.title},
        'image': None,
        'properties': [],
    }
