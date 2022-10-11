from io import StringIO

import pytest
from django.core.management import call_command
from model_bakery import baker

from nuremberg.documents.models import DocumentImage
from nuremberg.transcripts.models import TranscriptPage


pytestmark = pytest.mark.django_db


EXAMPLE_DOCUMENT_IMAGE_URL = '/proxy_image/HLSL_NUR_0001001.jpg'
EXAMPLE_TRANSCRIPT_IMAGE_URL = (
    '//s3.amazonaws.com/nuremberg-transcripts/NRMB-NMT01-01_00001.jpg'
)


def do_command_call(command_name='backfill_image_fields', **kwargs):
    stdout = StringIO()
    stderr = StringIO()
    result = call_command(command_name, stderr=stderr, stdout=stdout, **kwargs)
    return result, stdout, stderr


# document images


def test_backfill_document_image_url_backfilled():
    image_url_null = baker.make('DocumentImage', _url=None)
    image_url_static_cache = baker.make(
        'DocumentImage',
        image=None,
        _url='/static/image_cache/thumb/TEST_TEST_03799001.jpg',
    )
    image_url_printing = baker.make(
        'DocumentImage',
        image=None,
        _url='/proxy_image/printing/TEST_TEST_00198001.jpg',
    )
    image_url_regular = baker.make(
        'DocumentImage', image=None, _url='/proxy_image/TEST_TEST_03799352.jpg'
    )

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[
            image_url_null.document.id,
            image_url_static_cache.document.id,
            image_url_printing.document.id,
            image_url_regular.document.id,
        ],
        prefix='TEST_TEST_',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 3 DocumentImage(s).\n'
    assert stderr.getvalue() == ''

    assert not DocumentImage.objects.get(id=image_url_null.id).image.name
    assert DocumentImage.objects.get(id=image_url_null.id)._url is None

    assert (
        DocumentImage.objects.get(id=image_url_static_cache.id).image.path
        == '/media/TEST_TEST_03799001.jpg'
    )
    assert (
        DocumentImage.objects.get(id=image_url_static_cache.id)._url
        == image_url_static_cache._url
    )

    assert (
        DocumentImage.objects.get(id=image_url_printing.id).image.path
        == '/media/TEST_TEST_00198001.jpg'
    )
    assert (
        DocumentImage.objects.get(id=image_url_printing.id)._url
        == image_url_printing._url
    )

    assert (
        DocumentImage.objects.get(id=image_url_regular.id).image.path
        == '/media/TEST_TEST_03799352.jpg'
    )
    assert (
        DocumentImage.objects.get(id=image_url_regular.id)._url
        == image_url_regular._url
    )


def test_backfill_document_image_non_absolute_url(settings):
    settings.MEDIA_URL = '/foo/bar/'
    item = baker.make(
        'DocumentImage', image=None, _url=EXAMPLE_DOCUMENT_IMAGE_URL
    )

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[item.document.id],
        check=True,
        prefix='HLSL_NUR_',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 DocumentImage(s).\n'
    assert stderr.getvalue() == (
        'Can not validate non absolute URL '
        f'{settings.MEDIA_URL}HLSL_NUR_0001001.jpg.\n'
    )


def test_backfill_document_image_absolute_url(settings, requests_mock):
    settings.MEDIA_URL = 'http://doesnotexist.com/bar/'
    item = baker.make(
        'DocumentImage', image=None, _url='/proxy_image/IMG_0001001.jpg'
    )
    image_url = f'{settings.MEDIA_URL}IMG_0001001.jpg'
    requests_mock.head(image_url, status_code=404)

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[item.document.id],
        check=True,
        prefix='IMG_',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 DocumentImage(s).\n'
    assert stderr.getvalue() == (
        f'Image URL at {image_url} returned HTTP Code 404.\n'
    )


def test_backfill_document_image_no_matches():
    missing_doc_id = 123456789
    assert DocumentImage.objects.filter(id=missing_doc_id).count() == 0

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[missing_doc_id],
        prefix='HLSL_NUR_',
    )

    assert result is None
    assert stdout.getvalue() == ''
    assert stderr.getvalue() == 'No DocumentImage to be processed.\n'


def test_backfill_document_image_force():
    item = baker.make(
        'DocumentImage',
        image='something',
        _url=EXAMPLE_DOCUMENT_IMAGE_URL,
    )
    assert item.image.name

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[item.document.id],
        force=True,
        prefix='HLSL_NUR_',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 DocumentImage(s).\n'
    assert stderr.getvalue() == ''
    assert (
        DocumentImage.objects.get(id=item.id).image.path
        == '/media/HLSL_NUR_0001001.jpg'
    )
    assert DocumentImage.objects.get(id=item.id)._url == item._url


def test_backfill_document_image_not_force():
    item = baker.make(
        'DocumentImage',
        image='something',
        _url=EXAMPLE_DOCUMENT_IMAGE_URL,
    )
    assert item.image.name

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[item.document.id],
        force=False,
        prefix='HLSL_NUR_',
    )

    assert result is None
    assert stdout.getvalue() == ''
    assert stderr.getvalue() == 'No DocumentImage to be processed.\n'
    assert DocumentImage.objects.get(id=item.id).image.name == 'something'
    assert DocumentImage.objects.get(id=item.id)._url == item._url


def test_backfill_document_image_dry_run():
    item = baker.make(
        'DocumentImage',
        image=None,
        _url=EXAMPLE_DOCUMENT_IMAGE_URL,
    )

    result, stdout, stderr = do_command_call(
        documents=True,
        ids=[item.document.id],
        dry_run=True,
        prefix='HLSL_NUR_',
    )

    assert result is None
    assert stdout.getvalue() == 'Would have back filled 1 DocumentImage(s).\n'
    assert stderr.getvalue() == ''
    assert not DocumentImage.objects.get(id=item.id).image.name
    assert DocumentImage.objects.get(id=item.id)._url == item._url


# transcript pages


def test_backfill_transcript_page_url_backfilled():
    image_url_null = baker.make('TranscriptPage', _url=None)
    image_url_regular = baker.make(
        'TranscriptPage',
        image=None,
        _url='//s3.amazonaws.com/nuremberg-transcripts/TEST-TEST04-17_003.jpg',
    )

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[
            image_url_null.transcript.id,
            image_url_regular.transcript.id,
        ],
        prefix='TEST-TEST',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 TranscriptPage(s).\n'
    assert stderr.getvalue() == ''

    assert not TranscriptPage.objects.get(id=image_url_null.id).image.name
    assert TranscriptPage.objects.get(id=image_url_null.id)._url is None

    assert (
        TranscriptPage.objects.get(id=image_url_regular.id).image.path
        == '/media/TEST-TEST04-17_003.jpg'
    )
    assert (
        TranscriptPage.objects.get(id=image_url_regular.id)._url
        == image_url_regular._url
    )


def test_backfill_transcript_page_non_absolute_url(settings):
    settings.MEDIA_URL = '/foo/bar/'
    item = baker.make(
        'TranscriptPage',
        image=None,
        _url=EXAMPLE_TRANSCRIPT_IMAGE_URL,
    )

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[item.transcript.id],
        check=True,
        prefix='NRMB-NMT',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 TranscriptPage(s).\n'
    assert stderr.getvalue() == (
        'Can not validate non absolute URL '
        f'{settings.MEDIA_URL}NRMB-NMT01-01_00001.jpg.\n'
    )


def test_backfill_transcript_page_absolute_url(settings, requests_mock):
    settings.MEDIA_URL = 'http://doesnotexist.com/bar/'
    item = baker.make(
        'TranscriptPage', image=None, _url='/anything/at/all/IMG_0001001.jpg'
    )
    image_url = f'{settings.MEDIA_URL}IMG_0001001.jpg'
    requests_mock.head(image_url, status_code=404)

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[item.transcript.id],
        check=True,
        prefix='IMG_',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 TranscriptPage(s).\n'
    assert stderr.getvalue() == (
        f'Image URL at {image_url} returned HTTP Code 404.\n'
    )


def test_backfill_transcript_page_no_images():
    missing_doc_id = 123456789
    assert TranscriptPage.objects.filter(id=missing_doc_id).count() == 0

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[missing_doc_id],
        prefix='NRMB-NMT',
    )

    assert result is None
    assert stdout.getvalue() == ''
    assert stderr.getvalue() == 'No TranscriptPage to be processed.\n'


def test_backfill_transcript_page_force():
    item = baker.make(
        'TranscriptPage',
        image='something',
        _url=EXAMPLE_TRANSCRIPT_IMAGE_URL,
    )
    assert item.image.name

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[item.transcript.id],
        force=True,
        prefix='NRMB-NMT',
    )

    assert result is None
    assert stdout.getvalue() == 'Updated 1 TranscriptPage(s).\n'
    assert stderr.getvalue() == ''
    assert (
        TranscriptPage.objects.get(id=item.id).image.path
        == '/media/NRMB-NMT01-01_00001.jpg'
    )
    assert TranscriptPage.objects.get(id=item.id)._url == item._url


def test_backfill_transcript_page_not_force():
    item = baker.make(
        'TranscriptPage',
        image='something',
        _url=EXAMPLE_TRANSCRIPT_IMAGE_URL,
    )
    assert item.image.name

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[item.transcript.id],
        force=False,
        prefix='NRMB-NMT',
    )

    assert result is None
    assert stdout.getvalue() == ''
    assert stderr.getvalue() == 'No TranscriptPage to be processed.\n'
    assert TranscriptPage.objects.get(id=item.id).image.name == 'something'
    assert TranscriptPage.objects.get(id=item.id)._url == item._url


def test_backfill_transcript_page_dry_run():
    item = baker.make(
        'TranscriptPage',
        image=None,
        _url=EXAMPLE_TRANSCRIPT_IMAGE_URL,
    )

    result, stdout, stderr = do_command_call(
        transcripts=True,
        ids=[item.transcript.id],
        dry_run=True,
        prefix='NRMB-NMT',
    )

    assert result is None
    assert stdout.getvalue() == 'Would have back filled 1 TranscriptPage(s).\n'
    assert stderr.getvalue() == ''
    assert not TranscriptPage.objects.get(id=item.id).image.name
    assert TranscriptPage.objects.get(id=item.id)._url == item._url
