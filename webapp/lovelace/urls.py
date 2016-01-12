from django.conf.urls import include, url
from django.contrib import admin

# TODO: Design the url hierarchy from scratch
urlpatterns = [
    url(r'^admin/', include('smuggler.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^stats/', include('stats.urls', namespace='stats')),
    url(r'^feedback/', include('feedback.urls', namespace='feedback')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^', include('courses.urls', namespace='courses')),
]
