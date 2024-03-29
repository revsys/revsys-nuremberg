import datetime
import logging
from io import BytesIO

import requests


logger = logging.getLogger(__name__)


def do_request(url, method='GET', **kwargs):
    kwargs.setdefault('headers', {'User-Agent': 'Ubuntu; Linux x86_64'})
    kwargs.setdefault('allow_redirects', True)
    response = getattr(requests, method.lower())(url, **kwargs, timeout=5)
    if not response.ok:
        logger.error(
            f'Response for {method=} {url=} is not OK, got '
            f'{response.status_code=} with {response.headers=}'
        )
    return response


def download_and_store_image(
    image_url, image_path, media_storage, force=False
):
    bucket_name = getattr(media_storage, 'bucket_name', None)

    if media_storage.exists(image_path) and not force:
        logger.info(
            f'Will not download nor save {image_path=} in {bucket_name=} '
            f'because the path already exists (and {force=})'
        )
        return

    logger.info(f'Downloading {image_url=} to {image_path=} ({force=})')
    response = do_request(image_url)
    if not response.ok:
        return

    if force and media_storage.exists(image_path):
        logger.warning(
            f'Deleting {image_path=} in {bucket_name=} because {force=} and '
            f'the path already exists'
        )
        media_storage.delete(image_path)

    if not media_storage.exists(image_path):
        media_storage.save(image_path, BytesIO(response.content))
        logger.info(f'Saved {image_path=} in {bucket_name=}')


def build_image_path(image_url, image_name):
    image_headers = do_request(image_url, method='HEAD').headers
    content_type = image_headers.get('content-type')
    logger.debug(f'HEAD response for {image_url=} returned {image_headers=}')
    if not content_type.startswith('image/'):
        logger.error(
            f'Response for {image_url=} is not an image, got {content_type=}'
        )
        return None

    image_suffix = content_type.replace('image/', '')
    return f'{image_name}.{image_suffix}'


def parse_date(year, month, day, reference=None):
    try:
        result = datetime.date(year, month, day)
    except (TypeError, ValueError) as e:
        msg = 'Error parsing date for %s (got year %r, month %r, day %r): %s'
        if reference:
            logger.debug(
                msg,
                reference,
                year,
                month,
                day,
                e,
            )
        result = None
    return result
