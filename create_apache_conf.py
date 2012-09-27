import os

DJANGO_BASE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "django-project")
WSGI_DIR = os.path.join(DJANGO_BASE_DIR, "raippa")
WSGI_PATH = os.path.join(DJANGO_BASE_DIR, "raippa", "wsgi.py")

print "Django base directory: %s" % (DJANGO_BASE_DIR)
print "wsgi.py directory:     %s" % (WSGI_DIR)
print "wsgi.py path:          %s" % (WSGI_PATH)
print

HTTPD_CONF_TEMPLATE = \
"""WSGIScriptAlias / %s
WSGIPythonPath %s

<Directory %s>
    <Files wsgi.py>
        Order deny,allow
        Allow from all
    </Files>
</Directory>"""

print "Put this to your httpd.conf:"
print HTTPD_CONF_TEMPLATE % (WSGI_PATH, DJANGO_BASE_DIR, WSGI_DIR)

