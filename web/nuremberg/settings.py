import os
from pathlib import Path

import environ

# Load the environment smartly
env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(
    env.str(
        "BASE_DIR",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
)

LOCAL_DEVELOPMENT = env.bool("LOCAL_DEVELOPMENT", default=False)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "nuremberg",
    "nuremberg.core",
    "nuremberg.content",
    "nuremberg.documents",
    "nuremberg.transcripts",
    "nuremberg.photographs",
    "nuremberg.search",
    "compressor",
    "haystack",
    "static_precompiler",
    "django_vite",
    "corsheaders",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "nuremberg.core.middlewares.crawler.BlockCrawlerMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
]

ROOT_URLCONF = "nuremberg.core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "nuremberg.core.middlewares.context_processors.show_mockups",
                "nuremberg.core.middlewares.context_processors.settings_variables",
            ]
        },
    }
]

WSGI_APPLICATION = "nuremberg.wsgi.application"

SQLITE_DB_PATH = env("SQLITE_DB_PATH", default="nuremberg_dev.db")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SQLITE_DB_PATH,
        "USER": "nuremberg",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# compressor settings

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
    "static_precompiler.finders.StaticPrecompilerFinder",
]

COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.rCSSMinFilter",
]

# Compress supports precompilers, but static_precompiler has better watch features for dev
#
COMPRESS_PRECOMPILERS = (("text/less", "lessc {infile} {outfile}"),)

COMPRESS_STORAGE = "compressor.storage.OfflineManifestFileStorage"
COMPRESS_OFFLINE = True
COMPRESS_OFFLINE_MANIFEST = "compress-manifest.json"

# whitenoise settings
# https://warehouse.python.org/project/whitenoise/

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

STATICFILES_DIRS = [
    BASE_DIR.joinpath("frontend/dist/").as_posix(),
]

SOLR_URL = env("SOLR_URL", default="http://solr:8983/solr/nuremberg_dev")

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "nuremberg.search.lib.solr_grouping_backend.GroupedSolrEngine",
        "URL": SOLR_URL,
        "TIMEOUT": 60 * 5,
    }
}

HAYSTACK_DEFAULT_OPERATOR = "AND"
HAYSTACK_CUSTOM_HIGHLIGHTER = "nuremberg.core.highlighter.NurembergHighlighter"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"}
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
        }
    },
}


##############################################################################
# Deployed Settings
##############################################################################

CORS_ALLOW_ALL_ORIGINS = True

# file storage using django-storages
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html

AUTHORS_BUCKET = env(
    "AUTHORS_BUCKET", default="harvard-law-library-nuremberg-authors"
)
DOCUMENTS_BUCKET = env(
    "DOCUMENTS_BUCKET", default="harvard-law-library-nuremberg-documents"
)
TRANSCRIPTS_BUCKET = env(
    "TRANSCRIPTS_BUCKET",
    default="harvard-law-library-nuremberg-transcripts",
)

AWS_QUERYSTRING_AUTH = False

if not LOCAL_DEVELOPMENT:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    # AWS_S3_ACCESS_KEY_ID = env('AWS_S3_ACCESS_KEY_ID')
    # AWS_S3_SECRET_ACCESS_KEY = env('AWS_S3_SECRET_ACCESS_KEY')
    AWS_S3_REGION_NAME = "sfo2"
    AWS_S3_ENDPOINT_URL = (
        f"https://{AWS_S3_REGION_NAME}.digitaloceanspaces.com"
    )

# Look for images in AWS S3
# DOCUMENTS_URL = f'http://s3.amazonaws.com/nuremberg-documents/'
# TRANSCRIPTS_URL = f'http://s3.amazonaws.com/nuremberg-transcripts/'

#############################################################################
# ViteJS Settings
#############################################################################
DJANGO_VITE_DEV_MODE = env.bool("DJANGO_VITE_DEV_MODE", default=False)
DJANGO_VITE_DEV_SERVER_PORT = 5173
DJANGO_VITE_ASSETS_PATH = BASE_DIR.joinpath("frontend/dist/").as_posix()

##############################################################################
# Local Development Settings
##############################################################################

if LOCAL_DEVELOPMENT:
    SECRET_KEY = "supersecret"
    DEBUG = True
    COMPRESS_ENABLED = True
    COMPRESS_FORCE = False

    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }

    STATIC_PRECOMPILER_COMPILERS = (
        (
            "static_precompiler.compilers.LESS",
            {"executable": "lessc", "sourcemap_enabled": True},
        ),
    )

    # MIDDLEWARE_CLASSES.append('django_cprofile_middleware.middleware.ProfilerMiddleware')

    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    # Absolute filesystem path to the directory that will hold user-uploaded files.
    MEDIA_ROOT = os.path.abspath(os.path.join(BASE_DIR, "media"))
    MEDIA_URL = "/media/"
    MEDIA_URL = "https://sfo2.digitaloceanspaces.com/harvard-law-library-nuremberg-documents/"
    LOGGING["loggers"]["nuremberg"] = {
        "handlers": ["console"],
        "level": "INFO",
    }
