import os
import dotenv

def init_wsgi(dotenv_path):
    dotenv.load_dotenv(dotenv_path)

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    return application
