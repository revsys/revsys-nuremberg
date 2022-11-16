import logging
from io import BytesIO

import requests


logger = logging.getLogger(__name__)


def do_request(url, method='GET', **kwargs):
    kwargs.setdefault('headers', {'User-Agent': 'Ubuntu; Linux x86_64'})
    kwargs.setdefault('allow_redirects', True)
    response = getattr(requests, method.lower())(url, **kwargs)
    if not response.ok:
        logger.error(
            f'Response for {url=} is not OK, got {response.status_code=} with '
            f'{response.headers=}'
        )
    return response


def download_and_store_image(
    image_url, image_path, media_storage, force=False
):
    logger.info(f'Downloading {image_url=} into {image_path=} ({force=})')
    response = do_request(image_url)
    if not response.ok:
        return

    bucket_name = getattr(media_storage, 'bucket_name', 'local FS')

    if force and media_storage.exists(image_path):
        logger.warning(
            f'Deleting {image_path=} in {bucket_name=} because {force=} and '
            f'the path already exists'
        )
        media_storage.delete(image_path)

    if not media_storage.exists(image_path):
        media_storage.save(image_path, BytesIO(response.content))
        file_url = media_storage.url(image_path)
        logger.info(f'Saved {image_path=} in {bucket_name=} with {file_url=}')
    else:
        logger.error(
            f'Can not save {image_path=} in {bucket_name=} because the '
            f'path already exists (and {force=}).'
        )


def build_image_path(image_url, image_name):
    logger.debug(f'About to request HEAD for {image_url=}')
    image_headers = do_request(image_url, method='HEAD').headers
    content_type = image_headers.get('content-type')
    logger.debug(f'HEAD response for {image_url=} returned {image_headers=}')
    if not content_type.startswith('image/'):
        logger.error(
            f'Response for {image_url=} is not an image, got '
            f'{image_headers=}'
        )
        return None

    image_suffix = content_type.replace('image/', '')
    return f'{image_name}.{image_suffix}'
