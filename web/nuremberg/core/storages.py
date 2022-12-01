"""Customize storage backends for file fields.

This module has two functionalities:

1- Provide two custom storage classes to allow for Documents and Transcripts
to fetch media from dedicated S3-like buckets, and

2- Allow local development to use FileSystemStorage.


The former could be accomplished by just importing the `s3boto3` module like:

    from storages.backends import s3boto3

and defining two classes like:

    class DocumentStorage(s3boto3.S3Boto3Storage): ...

    class TranscriptStorage(s3boto3.S3Boto3Storage): ...


But, once we do the above, we need to define each `ImageField` in each model
(`DocumentImage` and `TranscriptPage`) to have their custom storage like:

    image = ImageField(..., storage=DocumentStorage(), ...)


Given the above, and in order to use the FileSystemStorage on local dev envs,
the settings have been defined so the generic setting have:

    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

but the dev settings have:

    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

So the new class `SettingsStorage` is effectively an instance of
`S3Boto3Storage` in all envs except on local where it's actually a
`FileSystemStorage` instance.

"""

from django.conf import settings
from django.utils.module_loading import import_string


SettingsStorage = import_string(settings.DEFAULT_FILE_STORAGE)


class AuthorStorage(SettingsStorage):
    bucket_name = settings.AUTHORS_BUCKET
    default_acl = 'public-read'


class DocumentStorage(SettingsStorage):
    bucket_name = settings.DOCUMENTS_BUCKET
    default_acl = 'public-read'


class TranscriptStorage(SettingsStorage):
    bucket_name = settings.TRANSCRIPTS_BUCKET
    default_acl = 'public-read'
