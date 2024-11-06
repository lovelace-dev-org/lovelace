"""
Django settings for Lovelace project. Do not modify this file.

This file takes all base settings from environment variables. The actual
DJANGO_SETTINGS_FILE environment variable should point to either dev.py or
production.py depending on your setup.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import json
import os
from kombu import Exchange, Queue

# To prevent accidents, unit tests will not run unless started with a settings
# file where this flag is set to True.
TEST_SETTINGS = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False # Use True when viewing through web browser

# Change to your hostname for production or network development installations
ALLOWED_HOSTS = os.environ["LOVELACE_HOSTNAME"].split(":") + [os.environ["LOVELACE_HOSTADDR"]]

# Applications
# If you want to use debug toolbar, copy this to your development settings file
# and uncomment the debug_toolbar line, then copy the MIDDLEWARE definition and
# uncomment the DebugToolbarMiddleware line
INSTALLED_APPS = [
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites', # Required by allauth
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'courses',
    'stats',
    'feedback',
    'routine_exercise',
    'faq',
    'assessment',
    'exercise_admin',
    'multiexam',
    'reversion',
    'teacher_tools',
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = int(os.getenv("LOVELACE_SITE_ID", 1))

# Shibboleth related options
if os.getenv("LOVELACE_USE_SHIBBOLETH"):
    ACCOUNT_USERNAME_VALIDATORS = "courses.adapter.username_validators"
    ACCOUNT_ADAPTER = "courses.adapter.LovelaceAccountAdapter"
    SHIBBOLETH_ATTRIBUTE_MAP = {
        "eppn": (True, "username"),
        "givenName": (True, "first_name"),
        "sn": (True, "last_name"),
        "mail": (True, "email"),
        "schacPersonalUniqueCode": (False, "student_id")
    }
    LOGIN_URL = "https://lovelace.oulu.fi/Shibboleth.sso/Login"

    #SHIBBOLETH_LOGOUT_URL = "https://login.oulu.fi/idp/logout?return=%s"
    SHIBBOLETH_LOGOUT_URL = "https://lovelace.oulu.fi/Shibboleth.sso/Logout?return=%s"
    SHIBBOLETH_LOGOUT_REDIRECT_URL = "https://lovelace.oulu.fi"

    INSTALLED_APPS.append("shibboleth")
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
        "courses.middleware.LovelaceShibbolethRemoteUser"
    )
    MIDDLEWARE.append("courses.middleware.ShibbolethExceptionReporter")
    AUTHENTICATION_BACKENDS.append("shibboleth.backends.ShibbolethRemoteUserBackend")


if os.getenv("ENABLE_MANAGEMENT_API"):
    ENABLE_MANAGEMENT_API = True
    INSTALLED_APPS.append("api")
    MANAGEMENT_API_KEY = os.environ["LOVELACE_MANAGEMENT_API_KEY"]
else:
    ENABLE_MANAGEMENT_API = False


if os.getenv("LOVELACE_PROMETHEUS_EXPORT"):
    INSTALLED_APPS.append("django_prometheus")
    MIDDLEWARE.insert(0, "django_prometheus.middleware.PrometheusBeforeMiddleware")
    MIDDLEWARE.append("django_prometheus.middleware.PrometheusAfterMiddleware")
    PROMETHEUS_ENABLED = True
else:
    PROMETHEUS_ENABLED = False



LOGIN_REDIRECT_URL = "/"
ROOT_URLCONF = "lovelace.urls"
TEMPLATES = (
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
)

UNEDITABLE_MARKUPS = ["empty", "cleanup", "error", "embedded", "calendar"]
ORPHAN_PREFIX = "null"

# Python dotted path to the WSGI application used by Django"s runserver.
WSGI_APPLICATION = "lovelace.wsgi.application"

# Extended UserProfile settings
AUTH_PROFILE_MODULE = "courses.UserProfile"


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
if os.getenv("LOVELACE_DB_USE_SSL"):
    _DB_OPTIONS = {
        "sslmode": "require",
        "sslcert": os.environ["LOVELACE_CLIENT_CERT"],
        "sslkey": os.environ["LOVELACE_CLIENT_KEY"],
        "sslrootcert": os.environ["LOVELACE_CLIENT_CA"],
    }
else:
    _DB_OPTIONS = {}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["LOVELACE_DB_NAME"],
        "USER": os.environ["LOVELACE_DB_USER"],
        "PASSWORD": os.environ["LOVELACE_DB_PASS"],
        "HOST": os.environ["LOVELACE_DB_HOST"],
        "PORT": os.environ["LOVELACE_DB_PORT"],
        "OPTIONS": _DB_OPTIONS,
    }
}


DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# E-mail backend settings
# Copy into your settings file and fill in your email server
# details
# Uncomment EMAIL_BACKEND if you want to log email into console instead for development
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_BACKEND = os.getenv(
    "LOVELACE_EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.getenv("LOVELACE_EMAIL_HOST", "localhost")
EMAIL_PORT = os.getenv("LOVELACE_EMAIL_PORT", 25)
EMAIL_HOST_USER = os.getenv("LOVELACE_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("LOVELACE_EMAIL_PWD", "")

# E-mail settings
EMAIL_SUBJECT_PREFIX = "[Lovelace] "
DEFAULT_FROM_EMAIL = os.getenv("LOVELACE_EMAIL_FROM", "lovelace-notify")

# Allauth settings
# For production, password min length of 32 or more recommended
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Lovelace] "
ACCOUNT_PASSWORD_MIN_LENGTH = 8
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SESSION_REMEMBER = True
ADMINS = [
    entry.rsplit(" ", 1) for entry in os.getenv("LOVELACE_ADMINS", "").split(":")
]
if os.getenv("LOVELACE_DISABLE_SIGNUP"):
    ACCOUNT_ADAPTER = "courses.adapter.PreventManualAccountsAdapter"

_FOUR_MONTHS = 10368000

ACCOUNT_SESSION_COOKIE_AGE = _FOUR_MONTHS
SESSION_COOKIE_AGE = _FOUR_MONTHS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "Europe/Helsinki"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = os.environ["LOVELACE_DEFAULT_LANG"]

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Set your available languages
LANGUAGES = (
    ("en", "English"),
    ("fi", "suomi"),
)

LOCALE_PATHS = (
    os.path.join(BASE_DIR, "locale"),
)

# Set the default language for modeltranslation
# This language will be used as the fallback content when translated content
# is not available
MODELTRANSLATION_DEFAULT_LANGUAGE = LANGUAGE_CODE
MODELTRANSLATION_FALLBACK_LANGUAGES = (
    [LANGUAGE_CODE]
    + [lang[0] for lang in LANGUAGES if lang[0] != LANGUAGE_CODE]
)

# URL prefix for static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_URL = "/static/"

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
# When creating a settings file for unit tests, change this to 
# os.path.join(BASE_DIR, "test_files", "upload") 
# or to a similarly isolated path. 
MEDIA_ROOT = os.environ["MEDIA_ROOT"]

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = "/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.environ["STATIC_ROOT"]
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "assets"),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don"t forget to use absolute paths, not relative paths.
)

TMP_PATH = "/tmp"

# Make this unique, and don"t share it with anybody.
SECRET_KEY = os.environ["LOVELACE_SECRET_KEY"]

# Redis settings for storing checking results
# If you change these in a configuration file,
# remember to also include the CELERY_RESULT_BACKEND definition to update it
REDIS_RESULT_EXPIRE = 60
REDIS_LONG_EXPIRE = 60 * 60 * 24 * 7

# Celery settings
# The default queue is used for checkers while the privileged queue is used
# for tasks that have elevated access and do not run any external code
import ssl

CELERY_BROKER_URL = os.environ["LOVELACE_CELERY_BROKER"]
CELERY_RESULT_BACKEND = os.environ["LOVELACE_CELERY_RESULT"]
if os.getenv("LOVELACE_CELERY_USE_SSL"):
    CELERY_BROKER_USE_SSL = {
        "cert_reqs": ssl.CERT_REQUIRED,
        "keyfile": os.environ["LOVELACE_CLIENT_KEY"],
        "certfile": os.environ["LOVELACE_CLIENT_CERT"],
        "ca_certs": os.environ["LOVELACE_CLIENT_CA"],
    }
    CELERY_RESULT_BACKEND += (
        "?ssl_cert_reqs=required"
        f"&ssl_ca_certs={os.environ['LOVELACE_CLIENT_CA']}"
        f"&ssl_certfile={os.environ['LOVELACE_CLIENT_CERT']}"
        f"&ssl_keyfile={os.environ['LOVELACE_CLIENT_KEY']}"
    )

CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"
CELERY_QUEUES = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("privileged", Exchange("privileged"), routing_key="privileged")
)
CELERY_ROUTES = {
    "teacher_tools.*": {
        "queue": "privileged",
        "exchange": "privileged",
        "routing_key": "privileged"
    },
    "stats.*": {
        "queue": "privileged",
        "exchange": "privileged",
        "routing_key": "privileged"
    }
}

# Cache settings
# If using the same redis server, use a different DB to keep it separate
# from checker results

if os.getenv("LOVELACE_CACHE_USE_SSL"):
    _CACHE_CONNECTION_POOL_KWARGS = {
        "ssl_cert_reqs": "required",
        "ssl_ca_certs": os.environ["LOVELACE_CLIENT_CA"],
        "ssl_certfile": os.environ["LOVELACE_CLIENT_CERT"],
        "ssl_keyfile": os.environ["LOVELACE_CLIENT_KEY"],
    }
else:
    _CACHE_CONNECTION_POOL_KWARGS = {}


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ["LOVELACE_REDIS_CACHE"],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": _CACHE_CONNECTION_POOL_KWARGS,
        }
    }
}

# Stats generation is a time-consuming task. This configuration key allows you
# to determine what hour of the day stats runs start
STAT_GENERATION_HOUR = None

# environment variables that are used when running student code in the checker
CHECKING_ENV = json.loads(os.environ["LOVELACE_CHECKER_ENV"])

# Usernames that are used by the checker to restrict what student code can do.
# Worker username is the worker"s own identity which it is demoted to immediately
# upon starting
# Restricted username is the user all student code is run as.
WORKER_USERNAME = os.getenv("LOVELACE_WORKER_USER", "nobody")
RESTRICTED_USERNAME = os.getenv("LOVELACE_RESTRICTED_USER", "nobody")


# Set PRIVATE_STORAGE_FS_PATH outside www root to make uploaded files
# inaccessible through URLs
# Set PRIVATE_STORAGE_X_SENDFILE to True if your configuration supports
# mod_xsendfile 
PRIVATE_STORAGE_FS_PATH = os.getenv("LOVELACE_PRIVATE_STORAGE", MEDIA_ROOT)
PRIVATE_STORAGE_X_SENDFILE = False

# Mossnet settings for code plagiarism checks
MOSSNET_SUBMIT_PATH = None
MOSSNET_LANGUAGES = []

CHECKER_PYTHON_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
