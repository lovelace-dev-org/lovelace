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

DJANGO_BASE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "webapp")
WSGI_DIR = os.path.join(DJANGO_BASE_DIR, "raippa")
WSGI_PATH = os.path.join(DJANGO_BASE_DIR, "raippa", "wsgi.py")
STATIC_DIR = os.path.join(DJANGO_BASE_DIR, "raippa", "static")
MEDIA_DIR = os.path.join(DJANGO_BASE_DIR, "upload")

# TODO: favicon.ico exception (/static/favicon.ico -> /favicon.ico)
# TODO: robots.txt exception
# TODO: Ensure that media (images etc.) are served directly by the web server (check urls.py)

print("Django base directory: %s" % (DJANGO_BASE_DIR))
print("wsgi.py directory:     %s" % (WSGI_DIR))
print("wsgi.py path:          %s" % (WSGI_PATH))
print()

HTTPD_CONF_STATICMEDIA_TEMPLATE = \
"""Alias /media/ %s/
Alias /static/ %s/

<Directory %s>
    Order deny,allow
    Allow from all
</Directory>

<Directory %s>
    Order deny,allow
    Allow from all
</Directory>"""

HTTPD_CONF_TEMPLATE = \
"""WSGIScriptAlias / %s
WSGIPythonPath %s

<Directory %s>
    <Files wsgi.py>
        Order deny,allow
        Allow from all
    </Files>
</Directory>"""

print("Put this to your httpd.conf:")
print(HTTPD_CONF_STATICMEDIA_TEMPLATE % (MEDIA_DIR, STATIC_DIR, STATIC_DIR, MEDIA_DIR))
print(HTTPD_CONF_TEMPLATE % (WSGI_PATH, DJANGO_BASE_DIR, WSGI_DIR))

