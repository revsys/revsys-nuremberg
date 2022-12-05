import datetime
import os
from io import BytesIO

import pytest

from nuremberg.documents.helpers import (
    build_image_path,
    do_request,
    download_and_store_image,
    parse_date,
)
from .helpers import DummyMemDictStorage, make_random_text


def test_do_request(requests_mock, caplog):
    url = 'https://example.com'
    text = make_random_text()
    requests_mock.get(url, text=text)

    response = do_request(url)

    assert response.ok
    assert response.content == text.encode('utf8')
    assert caplog.records == []


@pytest.mark.parametrize('method', ['HEAD', 'GET', 'PATCH', 'POST', 'PUT'])
def test_do_request_methods(requests_mock, caplog, method):
    url = 'https://example.com'
    text = make_random_text()
    getattr(requests_mock, method.lower())(url, text=text)

    response = do_request(url, method=method)

    assert response.ok
    assert response.content == text.encode('utf8')
    assert caplog.records == []


def test_do_request_not_ok(requests_mock, caplog):
    url = 'https://example.com'
    text = make_random_text()
    requests_mock.get(url, text=text, status_code=500)

    response = do_request(url)

    assert not response.ok
    assert response.content == text.encode('utf8')
    messages = [(x.levelname, x.message) for x in caplog.records]
    expected = (
        "Response for method='GET' url='https://example.com' is not OK, got "
        "response.status_code=500 with response.headers={}"
    )
    assert messages == [('ERROR', expected)]


def test_build_image_path(requests_mock, caplog):
    url = 'https://some-url/some-image.foo'
    name = 'any-name'
    requests_mock.head(url, headers={'content-type': 'image/png'})

    path = build_image_path(url, name)

    assert path == f'{name}.png'
    messages = [(x.levelname, x.message) for x in caplog.records]
    expected = (
        f"HEAD response for image_url={url!r} returned "
        "image_headers={'content-type': 'image/png'}"
    )
    assert messages == [('DEBUG', expected)]


def test_build_image_path_no_content_type_image(requests_mock, caplog):
    url = 'https://some-url/some-image.foo'
    name = 'any-name'
    requests_mock.head(url, headers={'content-type': 'no-image/png'})

    path = build_image_path(url, name)

    assert path is None
    messages = [
        (x.levelname, x.message)
        for x in caplog.records
        if x.levelname != 'DEBUG'
    ]
    expected = (
        f"Response for image_url={url!r} is not an image, got "
        "image_headers={'content-type': 'no-image/png'}"
    )
    assert messages == [('ERROR', expected)]


def test_download_and_store_image(requests_mock, caplog):
    url = 'https://some-url/some-image.foo'
    path = 'any-name.png'
    data = os.urandom(100)
    storage = DummyMemDictStorage()
    requests_mock.get(url, content=data)

    download_and_store_image(url, path, storage)

    assert storage.exists(path)
    assert storage.open(path).read() == data
    messages = [(x.levelname, x.message) for x in caplog.records]
    expected = [
        f'Downloading image_url={url!r} to image_path={path!r} (force=False)',
        f'Saved image_path={path!r} in bucket_name=None',
    ]
    assert messages == [('INFO', e) for e in expected]


def test_download_and_store_image_already_exists(requests_mock, caplog):
    url = 'https://some-url/some-image.foo'
    path = 'any-name.png'
    storage = DummyMemDictStorage()
    original = os.urandom(100)
    storage.save(path, BytesIO(original))
    data = os.urandom(100)
    requests_mock.get(url, content=data)

    download_and_store_image(url, path, storage)

    assert storage.exists(path)
    assert storage.open(path).read() == original
    messages = [(x.levelname, x.message) for x in caplog.records]
    info = (
        f'Downloading image_url={url!r} to image_path={path!r} (force=False)'
    )
    error = (
        f"Can not save image_path={path!r} in bucket_name=None "
        "because the path already exists (and force=False)"
    )
    assert messages == [('INFO', info), ('ERROR', error)]


def test_download_and_store_image_already_exists_force(requests_mock, caplog):
    url = 'https://some-url/some-image.foo'
    path = 'any-name.png'
    storage = DummyMemDictStorage()
    storage.save(path, BytesIO(os.urandom(100)))
    data = os.urandom(100)
    requests_mock.get(url, content=data)

    download_and_store_image(url, path, storage, force=True)

    assert storage.exists(path)
    assert storage.open(path).read() == data
    messages = [(x.levelname, x.message) for x in caplog.records]
    info = f'Downloading image_url={url!r} to image_path={path!r} (force=True)'
    warning = (
        f'Deleting image_path={path!r} in bucket_name=None because force=True '
        'and the path already exists'
    )
    assert messages == [
        ('INFO', info),
        ('WARNING', warning),
        ('INFO', f'Saved image_path={path!r} in bucket_name=None'),
    ]


@pytest.mark.parametrize('day', [None, 0, 33, -1])
@pytest.mark.parametrize('month', [None, 0, 13, -1])
@pytest.mark.parametrize('year', [None, 0, -1])
def test_document_date_invalid_date_params(day, month, year):
    d = parse_date(day=day, month=month, year=year)
    assert d is None


@pytest.mark.parametrize('year, month, day', [(2022, 2, 29), (2022, 4, 31)])
def test_document_date_invalid_date(day, month, year):
    d = parse_date(day=day, month=month, year=year)
    assert d is None


@pytest.mark.parametrize('day', [1, 30])
@pytest.mark.parametrize('month', [1, 12])
@pytest.mark.parametrize('year', [1, 1000, 2050])
def test_document_date_valid_as_date(day, month, year):
    d = parse_date(day=day, month=month, year=year)
    assert d == datetime.date(year, month, day)
