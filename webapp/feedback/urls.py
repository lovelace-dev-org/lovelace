from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^content/(?P<content_slug>[^/]+)/$', views.content, name='content'),
]
