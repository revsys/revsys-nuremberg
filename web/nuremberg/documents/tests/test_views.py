import pytest
from django.urls import reverse
from model_bakery import baker

from nuremberg.core.tests.acceptance_helpers import PyQuery, client
from nuremberg.documents.models import Document, DocumentPersonalAuthor
from .helpers import make_author


pytestmark = pytest.mark.django_db


def document(document_id):
    response = client.get(
        reverse('documents:show', kwargs={'document_id': document_id})
    )
    return PyQuery(response.content)


def test_document_1():
    page = document(1)

    assert Document.objects.get(id=1).title in page('h1').text()

    images = page('.document-image')
    assert len(images) == 20
    assert 'HLSL_NUR_00001001.jpg' in images.attr['data-screen-url']

    select = page('.page-buttons select')
    len(select.find('option')) == 20
    assert 'Sequence No. 20' in select.text()

    info = page('.document-info').text()
    assert "NMT 1" in info
    assert 'Date Unknown' in info
    assert 'Total Pages: 20' in info
    assert 'Language of Text: English' in info
    assert 'Source of Text: Case Files/English' in info
    assert 'HLSL Item No.: 1' in info


def test_document_2():
    page = document(2)

    assert (
        'Argument: prosecution closing argument against all defendants'
        in page('h1').text()
    )

    images = page('.document-image')
    assert len(images) == 78
    assert 'HLSL_NUR_00002001.jpg' in images.attr['data-screen-url']

    assert "Missing Image No. 13" in page.text()

    info = page('.document-info').text()
    assert 'NMT 1' in info
    assert '14 July 1947' in info
    assert 'Total Pages: 78' in info
    assert 'Language of Text: English' in info
    assert 'Source of Text: Case Files/English' in info
    assert 'HLSL Item No.: 2' in info


def test_document_400():
    page = document(400)

    assert (
        'Decree concerning the administration of Polish territories'
        in page('h1').text()
    )

    images = page('.document-image')
    assert len(images) == 3
    assert 'HLSL_NUR_00400001.jpg' in images.attr['data-screen-url']

    info = page('.document-info').text()
    assert 'NMT 1' in info
    assert '24 October 1939' in info
    assert 'Defendants\nKarl Gebhardt' in info
    assert 'Authors\nAdolf Hitler' in info
    assert 'Total Pages: 3' in info
    assert 'Language of Text: English' in info
    assert 'Source of Text: Case Files/English' in info
    assert 'HLSL Item No.: 400' in info
    assert 'Trial Issue\nSulfanilamide experiments' in info


def test_document_3799():
    page = document(3799)

    assert (
        'Journal and office records of Hans Frank, Governor General of Poland'
        ', 1939-1944' in page('h1').text()
    )

    images = page('.document-image img')
    assert len(images) == 492
    assert 'HLSL_NUR_03799492.jpg' in PyQuery(images[491]).attr['src']

    info = page('.document-info').text()
    assert 'NMT 1' not in info
    assert '02 December 1939' in info
    assert 'Author\nHans Frank' in info
    assert 'Total Pages: 492' in info
    assert 'Language of Text: German' in info
    assert 'Source of Text: Photostat' in info
    assert 'HLSL Item No.: 3799' in info


def assert_author_properties_html(
    response, name, description, image_url, image_alt, *properties
):
    assert response.status_code == 200
    assert 'text/html' in response.headers['Content-Type']

    content = PyQuery(response.content)

    # name is shown
    assert content.find('[data-test="author-name"]').text() == name

    # description is shown
    assert (
        content.find('[data-test="author-description"]').text() == description
    )

    # image is shown
    image = content.find('[data-test="author-image"]')
    assert len(image) == 1
    assert image[0].attrib['src'] == image_url
    assert image[0].attrib['alt'] == image_alt

    # other attributes
    items = content.find('[data-test="author-property"]')
    assert len(items) == len(properties)
    items = [  # remove html-insignificant spaces or \n
        ' '.join(j.strip() for j in i.text_content().strip().split())
        for i in items
    ]
    assert items == list(properties)


def test_author_properties_not_found():
    missing = 9999
    assert DocumentPersonalAuthor.objects.filter(id=missing).first() is None

    # request JSON
    response = client.get(
        reverse('documents:author', kwargs={'author_id': missing}),
        HTTP_ACCEPT='application/json',
    )

    assert response.status_code == 404

    # request HTML
    response = client.get(
        reverse('documents:author', kwargs={'author_id': missing})
    )

    assert response.status_code == 404


def test_author_properties_empty_properties():
    author = make_author()
    assert author.properties.all().count() == 0

    # request JSON
    response = client.get(
        reverse('documents:author', kwargs={'author_id': author.id}),
        HTTP_ACCEPT='application/json',
    )

    assert response.status_code == 200
    assert 'application/json' in response.headers['Content-Type']
    assert response.json() == {
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

    # request HTML
    response = client.get(
        reverse('documents:author', kwargs={'author_id': author.id})
    )

    image_url = '/static/images/authors/placeholder.png'
    image_alt = 'No image available.'
    assert_author_properties_html(
        response,
        author.full_name(),
        '',
        image_url,
        image_alt,
        'Additional biographical details not yet available.',
    )


def test_author_properties():
    author = make_author()
    description = 'A summary of the author'
    prop_image = baker.make(
        'PersonalAuthorProperty',
        personal_author_description='',
        personal_author=author,
        name='image',
        value='https://link-to-image-1.jpg',
    )
    image_alt = f'Image of {author.full_name()}'
    # other props, birth and occupation
    rank_place_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='place of birth', rank=28
    )
    rank_date_of_birth = baker.make(
        'PersonalAuthorPropertyRank', name='date of birth', rank=27
    )
    prop_place_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        personal_author_description='',
        name=rank_place_of_birth.name,
        value='A city',
        qualifier='',
        qualifier_value='',
    )
    prop_date_of_birth = baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        # description is taken from any property that has it
        personal_author_description=description,
        name=rank_date_of_birth.name,
        value='1979-01-01',
        qualifier='',
        qualifier_value='',
    )
    rank_occupation = baker.make(
        'PersonalAuthorPropertyRank', name='occupation', rank=26
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='soldier',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='politician',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='politician',
        qualifier='start time',
        qualifier_value='1925-01-01',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='politician',
        qualifier='end time',
        qualifier_value='1925-08-08',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='politician',
        qualifier='member of',
        qualifier_value='something',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='writer',
        qualifier='',
        qualifier_value='',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='writer',
        qualifier='point in time',
        qualifier_value='1923-11-09',
    )

    # request JSON
    response = client.get(
        reverse('documents:author', kwargs={'author_id': author.id}),
        HTTP_ACCEPT='application/json',
    )

    assert response.status_code == 200
    assert 'application/json' in response.headers['Content-Type']
    assert response.json() == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': description,
        },
        'image': {'url': prop_image.value, 'alt': image_alt},
        'properties': [
            {
                'name': 'born',
                'rank': 28,
                'prop_values': [
                    {'value': '1979-01-01 (A city)', 'qualifiers': []},
                ],
            },
            {
                'name': 'occupation',
                'rank': 26,
                'prop_values': [
                    {
                        'value': 'politician',
                        'qualifiers': [
                            ['member of', ['something']],
                            ['period', ['1925-01-01', '1925-08-08']],
                        ],
                    },
                    {'value': 'soldier', 'qualifiers': []},
                    {
                        'value': 'writer',
                        'qualifiers': [['date', ['1923-11-09']]],
                    },
                ],
            },
        ],
    }

    # request HTML (default)
    response = client.get(
        reverse('documents:author', kwargs={'author_id': author.id})
    )

    # occupation values are shown alphabetically ordered
    born = f'Born: {prop_date_of_birth.value} ({prop_place_of_birth.value})'
    occupation = (
        f'Occupation: politician (member of: something; period: 1925-01-01 '
        f'through 1925-08-08); soldier; writer (date: 1923-11-09)'
    )
    assert_author_properties_html(
        response,
        author.full_name(),
        description,
        prop_image.value,
        image_alt,
        born,
        occupation,
    )

    # request HTML using also author slug in URL
    response = client.get(
        reverse(
            'documents:author',
            kwargs={'author_id': author.id, 'author_slug': author.slug},
        )
    )

    assert_author_properties_html(
        response,
        author.full_name(),
        description,
        prop_image.value,
        image_alt,
        born,
        occupation,
    )
