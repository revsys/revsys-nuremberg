from nuremberg.settings import *

SECRET_KEY = "testing-secret"

COMPRESS_ENABLED = False
DEBUG = False

ALLOWED_HOSTS = ['web', 'localhost']

# Needed for template coverage report
TEMPLATES[0]['OPTIONS']['debug'] = True

# Any users are created and logged in faster with weak MD5 hasher
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# disable cache during tests
CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
}

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
