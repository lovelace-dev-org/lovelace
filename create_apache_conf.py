#!/usr/bin/env python
"""
Helper script for creating the appropriate settings for Apache HTTP Server.
Based on https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/modwsgi/

TODO: General configuration creator for the project:
      - Web server & WSGI: All combinations of (Apache|nginx)&(mod_wsgi|uWSGI)
      - Databases: Postgresql & sqlite3
      - RabbitMQ
      - Redis
"""
import os
import site

DJANGO_BASE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "webapp")
WSGI_DIR = os.path.join(DJANGO_BASE_DIR, "lovelace")
WSGI_PY_PATH = os.path.join(DJANGO_BASE_DIR, "lovelace", "wsgi.py")
SITE_PACKAGES_DIR = site.getsitepackages()[0] # for venv

STATIC_DIR = os.path.join(DJANGO_BASE_DIR, "static")
MEDIA_DIR = os.path.join(DJANGO_BASE_DIR, "upload")


# TODO: favicon.ico exception (/static/favicon.ico -> /favicon.ico)
# TODO: robots.txt exception
# TODO: Ensure that media (images etc.) are served directly by the web server (check urls.py)

print("Django base directory: %s" % (DJANGO_BASE_DIR))
print("wsgi.py directory:     %s" % (WSGI_DIR))
print("wsgi.py path:          %s" % (WSGI_PY_PATH))
print()

HTTPD_CONF_STATICMEDIA_TEMPLATE = \
"""
Alias /media/ %s/
Alias /static/ %s/

<Directory %s>
    Require all granted
</Directory>

<Directory %s>
    Require all granted
</Directory>
""".strip()

HTTPD_CONF_TEMPLATE = \
"""
WSGIScriptAlias / %s
WSGIPythonPath %s:%s

<Directory %s>
    <Files wsgi.py>
        Require all granted
    </Files>
</Directory>
""".strip()

print("Put this to your httpd.conf:")
print(HTTPD_CONF_STATICMEDIA_TEMPLATE % (MEDIA_DIR, STATIC_DIR, STATIC_DIR, MEDIA_DIR))
print(HTTPD_CONF_TEMPLATE % (WSGI_PY_PATH, DJANGO_BASE_DIR, SITE_PACKAGES_DIR, WSGI_DIR))

