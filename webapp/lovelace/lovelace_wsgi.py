import os
import dotenv

dotenv.load_dotenv()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

