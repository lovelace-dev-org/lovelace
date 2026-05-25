"""
Settings file for running celery workers. It only includes
installed apps and settings that are needed for running the
worker.
"""

import json
import os
import ssl
from kombu import Exchange, Queue
from dotenv import load_dotenv

load_dotenv(os.getenv("DOTENV_PATH"))

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'courses',
    'routine_exercise',
    'feedback',
    'stats',
    'teacher_tools',
]

TIME_ZONE = "Europe/Helsinki"
REDIS_RESULT_EXPIRE = 60

ENABLE_CELERY = True
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

TMP_PATH = "/tmp"
CHECKING_ENV = json.loads(os.environ["LOVELACE_CHECKER_ENV"])
WORKER_USERNAME = os.getenv("LOVELACE_WORKER_USER", "nobody")
RESTRICTED_USERNAME = os.getenv("LOVELACE_RESTRICTED_USER", "nobody")

WORKER_CONCURRENCY = os.getenv("LOVELACE_WORKER_CONCURRENCY", 40)
WORKER_NO_FILES = os.getenv("LOVELACE_WORKER_NO_FILES", 100)
WORKER_FILE_SIZE = os.getenv("LOVELACE_WORKER_FILE_SIZE", 4 * (1024 ** 2))
WORKER_CPU_TIME = os.getenv("LOVELACE_WORKER_CPU_TIME", 20)
WORKER_MEMORY = int(os.getenv("LOVELACE_WORKER_MEMORY", 100 * (1024 ** 2)))


MOSSNET_LANGUAGES = []
