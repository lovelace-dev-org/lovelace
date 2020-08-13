"""
Django settings for Lovelace project. Do not modify this file. In order to make
your own settings file(s), create them in the same folder with appropriate
names (recommended: development.py, production.py, unittest.py) and import the
contents of this file with: 

from lovelace.settings.factory import *

Then overwrite or modify the values you need to. You should also edit the
__init__.py in this folder to import the settings file you wish to use as the
default. When running manage.py you can change the settings file with the 
--settings option, e.g.

python manage.py --settings lovelace.settings.yoursettings

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import os
from kombu import Exchange, Queue

# to prevent accidents, unit tests will not run unless started with a settings
# file where this flag is set to True.
TEST_SETTINGS = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True # Use True when viewing through web browser

ALLOWED_HOSTS = ["localhost"]

# Applications
INSTALLED_APPS = (
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
    'exercise_admin',
    'routine_exercise',
    #'debug_toolbar',
    'reversion',
    'teacher_tools'
)

SITE_ID = 1
LOGIN_REDIRECT_URL = '/'

MIDDLEWARE = (
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'lovelace.urls'

TEMPLATES = (
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
)

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'lovelace.wsgi.application'

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydatabase',
        'USER': 'mydatabaseuser',
        'PASSWORD': 'mypassword',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# E-mail backend settings
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

# E-mail settings
EMAIL_SUBJECT_PREFIX = '[Lovelace] '
DEFAULT_FROM_EMAIL = 'lovelace-accounts@' # TODO: Fill!
#ADMINS = ( # TODO: Fill!
    #('Admin Name', 'admin@email'),
    #('Admin 2 Name', 'admin2@email'),
#)

# Allauth settings
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Lovelace] '
ACCOUNT_PASSWORD_MIN_LENGTH = 8
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SESSION_REMEMBER = True

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
TIME_ZONE = 'Europe/Helsinki'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

LANGUAGES = (
    ('en', 'English'),
    ('fi', 'suomi'),
)

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'

# URL prefix for static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_URL = '/static/'

# Extended UserProfile settings
AUTH_PROFILE_MODULE = 'courses.UserProfile'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
# When creating a settings file for unit tests, change this to 
# os.path.join(BASE_DIR, "test_files", "upload") 
# or to a similarly isolated path. 
MEDIA_ROOT = os.path.join(BASE_DIR, 'upload')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'assets'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

TMP_PATH = "/tmp"

# Make this unique, and don't share it with anybody.
SECRET_KEY = '$34r(o@3yfyr-=v8*ndtqm6^ti0=p%cyt&amp;a*giv-1w%q21r4ae'

# Redis settings
REDIS_RESULT_CONFIG = {"host": "localhost", "port": 6379, "db": 0}
REDIS_RESULT_EXPIRE = 60
REDIS_LONG_EXPIRE = 60 * 60 * 24 * 7

# Celery settings
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_RESULT_BACKEND = 'redis://{host}:{port}/{db}'.format(**REDIS_RESULT_CONFIG)
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
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

STAT_GENERATION_HOUR = None

CHECKING_ENV = {
    'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
    'LC_CTYPE': 'en_US.UTF-8',
}

WORKER_USERNAME = "nobody"
RESTRICTED_USERNAME = "nobody"

# Shibboleth related options - uncomment if using Shibboleth
# First one makes emails invalid usernames when creating accounts
# Second one is required for Shibboleth logout to work properly
#ACCOUNT_USERNAME_VALIDATORS = "courses.adapter.username_validators"
#ACCOUNT_ADAPTER = "courses.adapter.LovelaceAccountAdapter"

# Set PRIVATE_STORAGE_FS_PATH outside www root to make uploaded files
# inaccessible through URLs
# Set PRIVATE_STORAGE_X_SENDFILE to True if your configuration supports
# mod_xsendfile 
PRIVATE_STORAGE_FS_PATH = MEDIA_ROOT
PRIVATE_STORAGE_X_SENDFILE = False

MOSSNET_SUBMIT_PATH = None
MOSSNET_LANGUAGES = []

CHECKER_PYTHON_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
