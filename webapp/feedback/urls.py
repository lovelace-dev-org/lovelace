from django.conf.urls import patterns, include, url

from . import views

urlpatterns = [
    url(r'^content/(?P<content_slug>[^/]+)/$', views.content, name='content'),
]
