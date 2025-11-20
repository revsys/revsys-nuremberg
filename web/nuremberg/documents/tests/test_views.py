from urllib.parse import urlencode

import pytest
from django.urls import reverse
from model_bakery import baker

from nuremberg.core.tests.acceptance_helpers import PyQuery, client
from nuremberg.documents.models import (
    Document,
    DocumentPersonalAuthor,
    DocumentText,
)
from .helpers import (
    DummyMemDictStorage,
    make_author,
    make_document,
    make_random_text,
)


pytestmark = pytest.mark.django_db


def document_show_url(document_id, slug=None, **qs):
    kwargs = {'document_id': document_id}
    if slug is not None:
        kwargs['slug'] = slug
    url = reverse('documents:show', kwargs=kwargs)
    if qs:
        url += f'?{urlencode(qs)}'
    return url


def get_document(document_id=None, url=None, status_code=200, **qs):
    if url is None:
        assert document_id is not None
        url = document_show_url(document_id, **qs)

    response = client.get(url)

    assert response.status_code == status_code
    assert 'text/html' in response.headers['Content-Type']

    return PyQuery(response.content)


@pytest.mark.skip(reason="no longer valid after HLSL refactor")
def test_document_1():
    page = get_document(1)

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


@pytest.mark.skip(reason="no longer valid after HLSL refactor")
def test_document_2():
    page = get_document(2)

    assert (
        'Argument: prosecution closing argument against all defendants'
        in page('h1').text()
    )

    images = page('.document-image')
    assert len(images) == 78
    assert 'HLSL_NUR_00002001.jpg' in images.attr['data-screen-url']

    info = page('.document-info').text()
    assert 'NMT 1' in info
    assert '14 July 1947' in info
    assert 'Total Pages: 78' in info
    assert 'Language of Text: English' in info
    assert 'Source of Text: Case Files/English' in info
    assert 'HLSL Item No.: 2' in info


@pytest.mark.skip(reason="no longer valid after HLSL refactor")
def test_document_400():
    page = get_document(400)

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
    # Defendants are sorted by last name in the template
    assert 'Defendants: Fritz Fischer, Karl Gebhardt, Herta Oberheuser' in info
    assert 'Authors\nAdolf Hitler' in info
    assert 'Total Pages: 3' in info
    assert 'Language of Text: English' in info
    assert 'Source of Text: Case Files/English' in info
    assert 'HLSL Item No.: 400' in info
    assert 'Trial Issue\nSulfanilamide experiments' in info


@pytest.mark.skip(reason="no longer valid after HLSL refactor")
def test_document_3799():
    page = get_document(3799)

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
    assert 'Authors\nHans Frank' in info
    assert 'Government General of Occupied Polish Territories' in info
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
        'Additional details not yet available.',
    )


@pytest.mark.skip(reason="no longer valid after HLSL refactor")
def test_author_properties(requests_mock, monkeypatch):
    author = make_author()
    description = 'A summary of the author'
    image_url = 'https://link-to-image-1.jpg'
    baker.make(
        'PersonalAuthorProperty',
        personal_author_description='',
        personal_author=author,
        name='image',
        value=image_url,
    )
    # the author view would backfill the DocumentAuthorExtra instance, so the
    # remote link will be downloaded and stored locally in a dummy storage
    requests_mock.head(image_url, headers={'content-type': 'image/jpeg'})
    requests_mock.get(image_url, content=b'')
    monkeypatch.setattr(
        'nuremberg.documents.models.AuthorStorage', DummyMemDictStorage
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
        qualifier='start time',
        qualifier_value='1930-05-25',
    )
    baker.make(
        'PersonalAuthorProperty',
        personal_author=author,
        name=rank_occupation.name,
        value='politician',
        qualifier='end time',
        qualifier_value='1930-08-31',
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
    image_url = f'/media/{author.id}-{author.slug}.jpeg'
    assert response.json() == {
        'author': {
            'name': author.full_name(),
            'id': author.id,
            'slug': author.slug,
            'title': author.title,
            'description': description,
        },
        'image': {'url': image_url, 'alt': image_alt},
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
                            [
                                'period',
                                [
                                    ['1925-01-01', '1925-08-08'],
                                    ['1930-05-25', '1930-08-31'],
                                ],
                            ],
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
        'Occupation: politician (member of: something; period: 1925-01-01 '
        'through 1925-08-08, 1930-05-25 through 1930-08-31); soldier; '
        'writer (date: 1923-11-09)'
    )
    assert_author_properties_html(
        response,
        author.full_name(),
        description,
        image_url,
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
        image_url,
        image_alt,
        born,
        occupation,
    )


def test_document_image_not_found():
    assert Document.objects.filter(id=0).count() == 0
    get_document(document_id=0, status_code=404)


def test_document_text_not_found():
    assert DocumentText.objects.filter(id=0).count() == 0
    get_document(document_id=0, status_code=404, mode='text')


def test_document_details_no_full_text():
    doc = make_document(evidence_codes=[])

    content = get_document(doc.id)
    assert content.find('[data-test="full-text-view"]') == []
    assert content.find('[data-test="image-view"]') == []


def test_document_details_mode_text():
    doc = make_document(evidence_codes=['PPSS-123456'])
    full_text = baker.make(
        'DocumentText',
        text=make_random_text(150),
        evidence_code_series='PPSS',
        evidence_code_num='123456',
    )

    content = get_document(doc.id)
    links = content.find('[data-test="full-text-view"]')
    assert len(links) == 1

    text_view_url = document_show_url(
        full_text.id, slug=full_text.slug, mode='text'
    )
    [link] = links
    assert link.attrib['href'] == text_view_url
    assert link.text.strip() == 'Full-text View'
    assert content.find('[data-test="image-view"]') == []

    content = get_document(url=text_view_url)
    assert (
        content.find('[data-test="document-text-viewport"]').text()
        == full_text.text
    )


def test_document_details_mode_text_term_higlighting():
    doc = make_document(evidence_codes=['PPSS-123456'])
    text = make_random_text(150)
    full_text = baker.make(
        'DocumentText',
        text=text,
        evidence_code_series='PPSS',
        evidence_code_num='123456',
    )

    q = 'lorem ipsum'
    content = get_document(doc.id, q=q)
    links = content.find('[data-test="full-text-view"]')
    assert len(links) == 1

    text_view_url = document_show_url(
        full_text.id, slug=full_text.slug, mode='text', q=q
    )
    [link] = links
    assert link.attrib['href'] == text_view_url
    assert link.text.strip() == 'Full-text View'
    assert content.find('[data-test="image-view"]') == []

    # if a search term is carried from the search page, highlight the matches
    content = get_document(url=text_view_url)
    highlithed = full_text.text.replace(
        'Lorem', '<mark class="highlighted">Lorem</mark>'
    ).replace('ipsum', '<mark class="highlighted">ipsum</mark>')
    assert (
        content.find('[data-test="document-text-viewport"]').html().strip()
        == f'<p>{highlithed}</p>'
    )


def test_document_details_mode_text_term_higlighting_exact_phrase():
    doc = make_document(evidence_codes=['PPSS-123456'])
    # Taken from real document text ID 605
    text = (
        'After the customary removal of Jews from all public offices, the '
        'Jewish question will have to have a decisive solution, through the '
        'institution of Ghettos. Insofar as the Jews have not been driven out '
        'by the Ukrainians themselves, the small communities must be lodged '
        'in large camps, in order to be kept busy by means of forced labor, '
        'in the same way as it has already been the practice in '
        'Letzmanorstadt (Lodz). [Translation of paragraph, excluding all '
        'crossed out words.] After the customary removal of Jews from all '
        'public offices, the Jewish question will have to undergo a decisive '
        'solution through the institution of ghettos or labor battalions. '
        'Forced labor is to be introduced.'
    )

    full_text = baker.make(
        'DocumentText',
        text=text,
        evidence_code_series='PPSS',
        evidence_code_num='123456',
    )

    q = (
        '  lodged "  after the CuSTOMary removal of jews"   ghettos  '
        '"public offices"   CAmPS  '
    )
    content = get_document(doc.id, q=q)
    links = content.find('[data-test="full-text-view"]')
    assert len(links) == 1

    text_view_url = document_show_url(
        full_text.id, slug=full_text.slug, mode='text', q=q
    )
    [link] = links
    assert link.attrib['href'] == text_view_url
    assert link.text.strip() == 'Full-text View'
    assert content.find('[data-test="image-view"]') == []

    # if a search term is carried from the search page, highlight the matches
    content = get_document(url=text_view_url)
    actual_highligths = [h.text for h in content.find('mark.highlighted')]
    expected = [
        'After the customary removal of Jews',
        'public offices',
        'Ghettos',
        'lodged',
        'camps',
        'After the customary removal of Jews',
        'public offices',
        'ghettos',
    ]
    assert actual_highligths == expected
