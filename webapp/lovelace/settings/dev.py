from dotenv import load_dotenv
import os

load_dotenv(os.getenv("DOTENV_PATH"))

from lovelace.settings.factory import *

DEBUG = True
if os.getenv("DEBUG_TOOLBAR"):
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ["127.0.0.1"]
    extras = os.getenv("DEBUG_ACCESS_FROM")
    if extras:
        INTERNAL_IPS.extend(extras.split(","))

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
