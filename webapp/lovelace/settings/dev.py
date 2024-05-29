import os
from lovelace.settings.factory import *

DEBUG = True
if os.getenv("DEBUG_TOOLBAR"):
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}
