from django.conf.urls import patterns, include, url

from . import views

urlpatterns = [
    url(r'^content/(?P<content_slug>[^/]+)/$', views.content, name='content'),
    url(r'^(?P<content_slug>[^/]+)/(?P<feedback_slug>[^/]+)/receive/$', views.receive, name='receive'),
]
