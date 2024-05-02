import os
import sys
from lovelace.settings.factory import *

ALLOWED_HOSTS = [os.environ["LOVELACE_HOSTNAME"]]
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
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
        }
    },
    "loggers": {
        "": {
            "handlers": ["stdout", "stderr", "mail_admins"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    }
}

