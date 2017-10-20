from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView

# TODO: Design the url hierarchy from scratch
urlpatterns = [
    url(r'^admin/courses/fileuploadexercise/add', RedirectView.as_view(pattern_name='exercise_admin:file_upload_add')),
    url(r'^admin/courses/fileuploadexercise/(?P<exercise_id>\d+)/change', RedirectView.as_view(pattern_name='exercise_admin:file_upload_change')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^exercise-admin/', include('exercise_admin.urls', namespace='exercise_admin')),
    url(r'^stats/', include('stats.urls', namespace='stats')),
    url(r'^feedback/', include('feedback.urls', namespace='feedback')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^teacher/', include('teacher_tools.urls')),
]

try:
    urlpatterns.append(
        url(r'^shib/', include('shibboleth.urls', namespace='shibboleth'))
    )
except ImportError:
    # shibboleth is not installed
    pass
finally:
    urlpatterns.append(
        url(r'^', include('courses.urls', namespace='courses')),
    )

if settings.DEBUG:
    try:
        import debug_toolbar
    except ModuleNotFoundError:
        # Django Debug Toolbar not installed
        pass
    else:
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

