from lovelace.settings.factory import *

TEST_SETTINGS = True

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
    'routine_exercise',
    'faq',
    'assessment',
    'exercise_admin',
    #'debug_toolbar',
    'reversion',
    'teacher_tools',
)
LANGUAGE_CODE = 'fi'
MODELTRANSLATION_DEFAULT_LANGUAGE = 'fi'
MODELTRANSLATION_FALLBACK_LANGUAGES = ("fi", "en")

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

PRIVATE_STORAGE_FS_PATH = "/tmp/lovelace/test/upload"
MEDIA_ROOT = "/tmp/lovelace/test/upload"

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'lovelace',
        'USER': 'lovelace',
        'PASSWORD': 'hemuli',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

REDIS_RESULT_CONFIG = {"host": "localhost", "port": 6379, "db": 10}

CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_RESULT_CONFIG = {"host": "localhost", "port": 6379, "db": 10}
CELERY_RESULT_BACKEND = 'redis://{host}:{port}/{db}'.format(**CELERY_RESULT_CONFIG)


# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/11",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

WORKER_USERNAME = "enk"
RESTRICTED_USERNAME = "enk"

