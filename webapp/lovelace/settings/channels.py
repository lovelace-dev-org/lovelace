import os
from dotenv import load_dotenv

load_dotenv(os.getenv("DOTENV_PATH"))

ALLOWED_HOSTS = os.environ["LOVELACE_HOSTNAME"].split(":") + [os.environ["LOVELACE_HOSTADDR"]]

SECRET_KEY = os.environ["LOVELACE_SECRET_KEY"]
INSTALLED_APPS = [
    "daphne",
    "modeltranslation",
    "courses",
    "feedback",   # included because courses hard-depends on it
    "faq",        # included because courses soft-depends on it
    "task_ws",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

ASGI_APPLICATION = "lovelace.asgi.application"
ROOT_URLCONF = "lovelace.channel_urls"
ENABLE_CELERY = False
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

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
