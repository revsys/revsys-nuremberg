import datetime

import pytest
from model_bakery import baker

from nuremberg.documents.models import (
    DocumentDate,
    PersonalAuthorProperty,
    author_metadata,
)


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


def test_author_metadata_no_match():
    name = 'Does Not Exist'
    assert (
        PersonalAuthorProperty.objects.filter(
            personal_author_name=name
        ).count()
        == 0
    )

    result = author_metadata(name)

    assert result == {'author': {'name': name}, 'image': None, 'metadata': []}


def test_author_metadata_no_property_match():
    name = 'Does Not Exist'
    assert (
        PersonalAuthorProperty.objects.filter(
            personal_author_name=name
        ).count()
        == 0
    )
    author = baker.make(
        'DocumentPersonalAuthor',
        first_name='Does Not',
        last_name='Exist',
        title='Some Title',
    )

    result = author_metadata(name)

    metadata = [{'rank': 1, 'name': 'title', 'values': [author.title]}]
    assert result == {
        'author': {'name': name},
        'image': None,
        'metadata': metadata,
    }


def test_author_metadata_no_property_match_empty_title():
    name = 'Does Not Exist'
    assert (
        PersonalAuthorProperty.objects.filter(
            personal_author_name=name
        ).count()
        == 0
    )
    baker.make(
        'DocumentPersonalAuthor',
        first_name='Does Not',
        last_name='Exist',
        title='',
    )

    result = author_metadata(name)

    assert result == {'author': {'name': name}, 'image': None, 'metadata': []}


def test_author_metadata_uses_property_ranks():
    author = baker.make(
        'DocumentPersonalAuthor', first_name='Some', last_name='Name'
    )

    rank0 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank 0', rank=0
    )
    prop0 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=author.full_name(),
        name=rank0.name,
        entity='Ignored 0',
    )
    assert prop0.rank == 0

    rank_negative_1 = baker.make(
        'PersonalAuthorPropertyRank', name='ignore due to rank -1', rank=-1
    )
    prop_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=author.full_name(),
        name=rank_negative_1.name,
        entity='Ignored -1',
    )
    assert prop_1.rank == -1

    prop_none = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=author.full_name(),
        name='no rank available',
        entity='Ignored None',
    )
    assert prop_none.rank is None

    rank_1 = baker.make('PersonalAuthorPropertyRank', name='valid 1', rank=1)
    prop_1_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=author.full_name(),
        name=rank_1.name,
        entity='one value',
    )
    assert prop_1_1.rank == 1
    prop_1_2 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=author.full_name(),
        name=rank_1.name,
        entity='another',
    )
    assert prop_1_2.rank == 1

    rank_5 = baker.make('PersonalAuthorPropertyRank', name='valid 5', rank=5)
    prop_5 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=author.full_name(),
        name=rank_5.name,
        entity='different value, could be a link who knows',
    )
    assert prop_5.rank == 5

    result = author_metadata(author.full_name())

    # order is given by higher rank first, then entity
    expected = [
        {'rank': 5, 'name': 'valid 5', 'values': [prop_5.entity]},
        {'rank': 1, 'name': 'valid 1', 'values': ['another', 'one value']},
    ]
    assert result == {
        'author': {'name': author.full_name()},
        'image': None,
        'metadata': expected,
    }


def test_author_metadata_extracts_image():
    author = baker.make(
        'DocumentPersonalAuthor',
        first_name='Some Other',
        last_name='Name',
        title='Sir Someone',
    )
    name = author.full_name()

    rank_image = baker.make(
        'PersonalAuthorPropertyRank', name='image', rank=30
    )
    prop_image_1 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_image.name,
        entity='https://link-to-image-1.jpg',
    )
    assert prop_image_1.rank == 30
    prop_image_2 = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_image.name,
        entity='https://link-to-image-2.jpg',
    )
    assert prop_image_2.rank == 30

    result = author_metadata(name)

    metadata = [{'rank': 1, 'name': 'title', 'values': [author.title]}]
    # XXX: alt needs data definition, waiting on Paul for this
    image = {'url': prop_image_1.entity, 'alt': f'Image of {name}'}
    assert result == {
        'author': {'name': name},
        'image': image,
        'metadata': metadata,
    }


def test_author_metadata_groups_birth_data():
    name = 'John Doe'
    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=24
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=23
    )
    prop_place_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_place_of_birth.name,
        entity='A city or location',
    )
    prop_date_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_date_of_birth.name,
        entity='1979-01-01',
    )

    result = author_metadata(name)

    metadata = [
        {
            'rank': 24,
            'name': 'born',
            'values': [prop_place_of_birth.entity, prop_date_of_birth.entity],
        }
    ]
    assert result == {
        'author': {'name': name},
        'image': None,
        'metadata': metadata,
    }


def test_author_metadata_groups_death_data():
    name = 'John Doe'
    rank_place_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='place of death', rank=24
    )
    rank_date_of_death = baker.make(
        'PersonalAuthorPropertyRank', name='date of death', rank=23
    )
    prop_place_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_place_of_death.name,
        entity='A city or location',
    )
    prop_date_of_death = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_date_of_death.name,
        entity='1979-01-01',
    )

    result = author_metadata(name)

    metadata = [
        {
            'rank': 24,
            'name': 'died',
            'values': [prop_place_of_death.entity, prop_date_of_death.entity],
        }
    ]
    assert result == {
        'author': {'name': name},
        'image': None,
        'metadata': metadata,
    }


def test_author_metadata_groups_name_data():
    name = 'John Doe'
    rank_family_name = baker.make(
        'PersonalAuthorPropertyRank', name='family name', rank=28
    )
    rank_given_name = baker.make(
        'PersonalAuthorPropertyRank', name='given name', rank=27
    )
    prop_family_name = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_family_name.name,
        entity='Family Name',
    )
    prop_given_name = baker.make(
        'PersonalAuthorProperty',
        personal_author_name=name,
        name=rank_given_name.name,
        entity='Given Name',
    )

    result = author_metadata(name)

    metadata = [
        {
            'rank': 28,
            'name': 'name',
            'values': [prop_family_name.entity, prop_given_name.entity],
        }
    ]
    assert result == {
        'author': {'name': name},
        'image': None,
        'metadata': metadata,
    }
