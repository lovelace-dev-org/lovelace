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
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# To prevent accidents, unit tests will not run unless started with a settings
# file where this flag is set to True.
TEST_SETTINGS = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True # Use True when viewing through web browser

# Change to your hostname for production or network development installations
ALLOWED_HOSTS = [os.environ["LOVELACE_HOSTNAME"], os.environ["LOVELACE_HOSTADDR"]]

# Applications
# If you want to use debug toolbar, copy this to your development settings file
# and uncomment the debug_toolbar line, then copy the MIDDLEWARE definition and
# uncomment the DebugToolbarMiddleware line
INSTALLED_APPS = (
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites", # Required by allauth
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "courses",
    "stats",
    "feedback",
    "exercise_admin",
    "routine_exercise",
    "faq",
    "assessment",
    "reversion",
    "teacher_tools"
)

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

SITE_ID = 1
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

# Python dotted path to the WSGI application used by Django"s runserver.
WSGI_APPLICATION = "lovelace.wsgi.application"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Extended UserProfile settings
AUTH_PROFILE_MODULE = "courses.UserProfile"


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["LOVELACE_DB_NAME"],
        "USER": os.environ["LOVELACE_DB_USER"],
        "PASSWORD": os.environ["LOVELACE_DB_PASS"],
        "HOST": os.environ["LOVELACE_DB_HOST"],
        "PORT": os.environ["LOVELACE_DB_PORT"],
    }
}


DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# E-mail backend settings
# Copy into your settings file and fill in your email server
# details
# Uncomment EMAIL_BACKEND if you want to log email into console instead for development
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.environ.get("LOVELACE_EMAIL_HOST", "localhost")
EMAIL_PORT = os.environ.get("LOVELACE_EMAIL_PORT", 25)
EMAIL_HOST_USER = os.environ.get("LOVELACE_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("LOVELACE_EMAIL_PWD", "")

# E-mail settings
EMAIL_SUBJECT_PREFIX = "[Lovelace] "
DEFAULT_FROM_EMAIL = "lovelace-notify@"

# Allauth settings
# For production, password min length of 32 or more recommended
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Lovelace] "
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
MODELTRANSLATION_FALLBACK_LANGUAGES = [LANGUAGE_CODE] + [lang[0] for lang in LANGUAGES]

# URL prefix for static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_URL = "/static/"

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
# When creating a settings file for unit tests, change this to 
# os.path.join(BASE_DIR, "test_files", "upload") 
# or to a similarly isolated path. 
MEDIA_ROOT = os.path.join(BASE_DIR, "upload")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = "/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
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
REDIS_RESULT_CONFIG = {
    "host": os.environ["LOVELACE_REDIS_HOST"],
    "port": os.environ["LOVELACE_REDIS_PORT"],
    "db": os.environ["LOVELACE_REDIS_RESULT_DB"],
}
REDIS_RESULT_EXPIRE = 60
REDIS_LONG_EXPIRE = 60 * 60 * 24 * 7

# Celery settings
# The default queue is used for checkers while the privileged queue is used
# for tasks that have elevated access and do not run any external code
CELERY_BROKER_URL = os.environ["LOVELACE_CELERY_BROKER"]
CELERY_RESULT_BACKEND = "redis://{host}:{port}/{db}".format(**REDIS_RESULT_CONFIG)
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
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ["LOVELACE_REDIS_CACHE"],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Stats generation is a time-consuming task. This configuration key allows you
# to determine what hour of the day stats runs start
STAT_GENERATION_HOUR = None

# environment variables that are used when running student code in the checker
CHECKING_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LC_CTYPE": "en_US.UTF-8",
}

# Usernames that are used by the checker to restrict what student code can do.
# Worker username is the worker"s own identity which it is demoted to immediately
# upon starting
# Restricted username is the user all student code is run as.
WORKER_USERNAME = os.environ.get("LOVELACE_WORKER_USER", "nobody")
RESTRICTED_USERNAME = os.environ.get("LOVELACE_RESTRICTED_USER", "nobody")

# Shibboleth related options - uncomment if using Shibboleth
# First one makes emails invalid usernames when creating accounts
# Second one is required for Shibboleth logout to work properly
#ACCOUNT_USERNAME_VALIDATORS = "courses.adapter.username_validators"
#ACCOUNT_ADAPTER = "courses.adapter.LovelaceAccountAdapter"

# Set PRIVATE_STORAGE_FS_PATH outside www root to make uploaded files
# inaccessible through URLs
# Set PRIVATE_STORAGE_X_SENDFILE to True if your configuration supports
# mod_xsendfile 
PRIVATE_STORAGE_FS_PATH = os.environ.get("LOVELACE_PRIVATE_STORAGE", MEDIA_ROOT)
PRIVATE_STORAGE_X_SENDFILE = False

# Mossnet settings for code plagiarism checks
MOSSNET_SUBMIT_PATH = None
MOSSNET_LANGUAGES = []

CHECKER_PYTHON_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
