from django.conf.urls import include, url

from . import views

urlpatterns = [
    
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/download_answers/$', views.download_answers, name="download_answers")
    
]

