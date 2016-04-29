from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^statistics/(?P<content_slug>[^/]+)/$', views.content_feedback_stats, name='statistics'),
    url(r'^(?P<content_slug>[^/]+)/(?P<feedback_slug>[^/]+)/receive/$', views.receive, name='receive'),
]
