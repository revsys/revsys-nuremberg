import environ
import os


# Load the environment smartly
env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'nuremberg',
    'nuremberg.core',
    'nuremberg.content',
    'nuremberg.documents',
    'nuremberg.transcripts',
    'nuremberg.photographs',
    'nuremberg.search',
    'compressor',
    'haystack',
    'static_precompiler',
]

MIDDLEWARE = [
    'nuremberg.core.middlewares.crawler.BlockCrawlerMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
]

ROOT_URLCONF = 'nuremberg.core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'nuremberg.core.middlewares.context_processors.show_mockups',
                'nuremberg.core.middlewares.context_processors.settings_variables',
            ]
        },
    }
]

WSGI_APPLICATION = 'nuremberg.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'nuremberg_dev.db',
        'USER': 'nuremberg',
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]


# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# compressor settings

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]

# Compress supports precompilers, but static_precompiler has better watch features for dev
#
# COMPRESS_PRECOMPILERS = (
#     ('text/less', 'lessc {infile} {outfile}'),
# )

COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'

# whitenoise settings
# https://warehouse.python.org/project/whitenoise/

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'nuremberg.search.lib.solr_grouping_backend.GroupedSolrEngine',
        'URL': 'http://solr:8983/solr/nuremberg_dev',
        'TIMEOUT': 60 * 5,
    }
}
HAYSTACK_DEFAULT_OPERATOR = 'AND'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env.str('DJANGO_LOG_LEVEL', default='INFO'),
        }
    },
}


LOCAL_DEVELOPMENT = env.bool("LOCAL_DEVELOPMENT", default=False)

##############################################################################
# Deployed Settings
##############################################################################

# file storage using django-storages
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html

AUTHORS_BUCKET = env(
    "AUTHORS_BUCKET", default='harvard-law-library-nuremberg-authors'
)
DOCUMENTS_BUCKET = env(
    "DOCUMENTS_BUCKET", default='harvard-law-library-nuremberg-documents'
)
TRANSCRIPTS_BUCKET = env(
    "TRANSCRIPTS_BUCKET",
    default='harvard-law-library-nuremberg-transcripts',
)

if not LOCAL_DEVELOPMENT:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_S3_ACCESS_KEY_ID = env('AWS_S3_ACCESS_KEY_ID')
    AWS_S3_SECRET_ACCESS_KEY = env('AWS_S3_SECRET_ACCESS_KEY')
    AWS_S3_REGION_NAME = 'sfo2'
    AWS_S3_ENDPOINT_URL = (
        f'https://{AWS_S3_REGION_NAME}.digitaloceanspaces.com'
    )

# Look for images in AWS S3
# DOCUMENTS_URL = f'http://s3.amazonaws.com/nuremberg-documents/'
# TRANSCRIPTS_URL = f'http://s3.amazonaws.com/nuremberg-transcripts/'


##############################################################################
# Local Development Settings
##############################################################################

if LOCAL_DEVELOPMENT:
    SECRET_KEY = 'supersecret'
    DEBUG = True
    COMPRESS_ENABLED = False

    CACHES = {
        'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
    }

    STATIC_PRECOMPILER_COMPILERS = (
        (
            'static_precompiler.compilers.LESS',
            {"executable": "lessc", "sourcemap_enabled": True},
        ),
    )

    # MIDDLEWARE_CLASSES.append('django_cprofile_middleware.middleware.ProfilerMiddleware')

    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    # Absolute filesystem path to the directory that will hold user-uploaded files.
    MEDIA_ROOT = os.path.abspath(os.path.join(BASE_DIR, 'media'))
    MEDIA_URL = '/media/'
