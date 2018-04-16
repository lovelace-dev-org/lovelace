from django.conf.urls import url

from . import views

app_name = "feedback"

urlpatterns = [
    url(r'^statistics/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/$', views.content_feedback_stats, name='statistics'),
    url(r'^(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/(?P<feedback_slug>[^/]+)/receive/$', views.receive, name='receive'),
]
