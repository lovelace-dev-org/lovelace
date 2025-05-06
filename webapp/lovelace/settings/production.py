import os
import sys
from lovelace.settings.factory import *

ALLOWED_HOSTS = os.environ["LOVELACE_HOSTNAME"].split(":")
DEBUG = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{levelname}] lovelace {name}: {message}",
            "style": "{",
        },
    },
    "filters": {
        "cap_stdout": {
            "()": "utils.logging.LogLevelCap",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "filters": ["cap_stdout"],
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
            "level": "WARNING",
        },
        # Commented out since existing loggers already do this
        #"mail_admins": {
        #    "level": "ERROR",
        #    "class": "django.utils.log.AdminEmailHandler",
        #}
    },
    "loggers": {
        "": {
            "handlers": ["stdout", "stderr"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    }
}

# In production mode remove all variables containing secrets
# from env so that they do not end up in logs etc. by accident

_PROTECTED_KEYS = [
    "LOVELACE_CELERY_BROKER",
    "LOVELACE_CELERY_RESULT",
    "LOVELACE_SECRET_KEY",
    "LOVELACE_REDIS_CACHE",
    "LOVELACE_DB_PASS",
    "LOVELACE_DB_HOST",
    "LOVELACE_DB_PORT",
    "LOVELACE_ADMINS",
]
for key in _PROTECTED_KEYS:
    try:
        del os.environ[key]
    except KeyError:
        pass



